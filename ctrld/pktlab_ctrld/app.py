"""Controller runtime state and service composition."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from pktlab_ctrld import __version__
from pktlab_ctrld.config.validation import ValidatedTopologyConfig
from pktlab_ctrld.error import ErrorCode, PktlabError
from pktlab_ctrld.process.supervisor import DatapathProcessStatus, DpdkdSupervisor, SupervisorConfig
from pktlab_ctrld.state.desired import ControllerStateValue, DesiredState
from pktlab_ctrld.state.observed import ObservedState
from pktlab_ctrld.topology.manager import TopologyManager, TopologyOperationResult
from pktlab_ctrld.types import EffectiveDpdkRuntimeModel
from pktlab_ctrld.util.netns import NetnsRunner


@dataclass(frozen=True, slots=True)
class ControllerConfig:
    """Runtime configuration for the controller service."""

    datapath_binary: str
    datapath_socket_path: str
    datapath_startup_timeout_seconds: float = 5.0
    supervise_datapath: bool = True

    def __post_init__(self) -> None:
        if not self.datapath_binary.strip():
            raise ValueError("datapath_binary must be a non-empty string")
        if not self.datapath_socket_path.strip():
            raise ValueError("datapath_socket_path must be a non-empty string")
        if self.datapath_startup_timeout_seconds <= 0:
            raise ValueError("datapath_startup_timeout_seconds must be greater than zero")


@dataclass(frozen=True, slots=True)
class ControllerHealthSnapshot:
    """Controller-visible runtime health snapshot."""

    controller_service: str
    controller_version: str
    controller_state: ControllerStateValue
    controller_message: str
    desired_state: DesiredState
    observed_state: ObservedState
    datapath_status: DatapathProcessStatus


class ControllerRuntime:
    """Own controller lifecycle, datapath supervision, and health reporting."""

    def __init__(
        self,
        config: ControllerConfig,
        *,
        supervisor: DpdkdSupervisor | None = None,
        topology_manager: TopologyManager | None = None,
        netns_runner: NetnsRunner | None = None,
    ) -> None:
        self.config = config
        self._lock = RLock()
        self._desired_state = DesiredState(
            desired_controller_state="stopped",
            desired_datapath_running=config.supervise_datapath,
        )
        self._observed_state = ObservedState()
        self._controller_state: ControllerStateValue = "stopped"
        self._controller_message = "controller is not started"
        self._controller_override_message: str | None = None
        self._started = False
        self._supervisor = supervisor
        self._netns_runner = netns_runner or NetnsRunner()
        if self._supervisor is None and config.supervise_datapath:
            self._supervisor = DpdkdSupervisor(self._build_supervisor_config())
        self._topology_manager = topology_manager or TopologyManager(
            netns=self._netns_runner,
            start_datapath=self._start_topology_datapath,
            stop_datapath=self._stop_topology_datapath,
        )

    @property
    def desired_state(self) -> DesiredState:
        """Return the current desired state snapshot."""

        return self._desired_state

    @property
    def observed_state(self) -> ObservedState:
        """Return the current observed state snapshot."""

        return self._observed_state

    def start(self) -> None:
        """Start controller-managed services."""

        with self._lock:
            if self._started:
                return

            self._clear_controller_override()
            self._controller_state = "starting"
            self._controller_message = "starting controller runtime"
            self._desired_state = DesiredState(
                desired_controller_state="running",
                desired_datapath_running=self.config.supervise_datapath,
            )

            datapath_status = self._unmanaged_datapath_status()
            if self._supervisor is not None:
                datapath_status = self._supervisor.start()

            self._observed_state = self._observed_from_datapath(
                datapath_status,
                topology_applied=self._observed_state.topology_applied,
                effective_dpdk_config=self._observed_state.effective_dpdk_config,
            )
            self._started = True
            self._recompute_controller_health(datapath_status)

    def stop(self) -> None:
        """Stop controller-managed services."""

        with self._lock:
            if not self._started:
                return

            self._clear_controller_override()
            self._controller_state = "stopping"
            self._controller_message = "stopping controller runtime"

            if self._topology_manager.has_applied_topology:
                self._topology_manager.destroy()
            elif self._supervisor is not None:
                self._supervisor.stop()

            self._observed_state = self._observed_from_datapath(
                self._unmanaged_datapath_status(),
                topology_applied=False,
                effective_dpdk_config=None,
            )
            self._desired_state = DesiredState(
                desired_controller_state="stopped",
                desired_datapath_running=False,
            )
            self._controller_state = "stopped"
            self._controller_message = "controller stopped"
            self._started = False

    def apply_topology(self, config_path: str) -> TopologyOperationResult:
        """Apply a validated topology through the topology manager."""

        if not config_path.strip():
            raise ValueError("config_path must be a non-empty string")
        with self._lock:
            self._clear_controller_override()
            self._controller_state = "reconciling"
            self._controller_message = f"applying topology from {config_path}"

        try:
            result = self._topology_manager.apply(config_path)
        except Exception:
            with self._lock:
                datapath_status = self._current_datapath_status_locked()
                if not self._topology_manager.has_applied_topology:
                    self._desired_state = self._desired_state_without_topology()
                    self._observed_state = self._observed_from_datapath(
                        datapath_status,
                        topology_applied=False,
                        effective_dpdk_config=None,
                    )
                else:
                    self._observed_state = self._observed_from_datapath(
                        datapath_status,
                        topology_applied=self._observed_state.topology_applied,
                        effective_dpdk_config=self._observed_state.effective_dpdk_config,
                    )
                self._controller_override_message = f"failed to apply topology from {config_path}"
                self._recompute_controller_health(datapath_status)
            raise

        with self._lock:
            self._clear_controller_override()
            self._desired_state = DesiredState(
                topology_config_path=result.config_path,
                topology_name=result.topology_name,
                requested_dpdk_config=result.requested_dpdk_config,
                desired_controller_state="running",
                desired_datapath_running=result.applied,
            )
            datapath_status = self._current_datapath_status_locked()
            self._observed_state = self._observed_from_datapath(
                datapath_status,
                topology_applied=result.applied,
                effective_dpdk_config=result.effective_dpdk_config,
            )
            self._recompute_controller_health(datapath_status)
        return result

    def destroy_topology(self) -> TopologyOperationResult:
        """Destroy the currently applied topology if one exists."""

        with self._lock:
            self._clear_controller_override()
            self._controller_state = "reconciling"
            self._controller_message = "destroying topology"

        try:
            result = self._topology_manager.destroy()
        except Exception:
            with self._lock:
                datapath_status = self._current_datapath_status_locked()
                self._observed_state = self._observed_from_datapath(
                    datapath_status,
                    topology_applied=self._observed_state.topology_applied,
                    effective_dpdk_config=self._observed_state.effective_dpdk_config,
                )
                self._controller_override_message = "failed to destroy topology"
                self._recompute_controller_health(datapath_status)
            raise

        self._stop_topology_datapath()
        with self._lock:
            self._clear_controller_override()
            self._desired_state = self._desired_state_without_topology()
            datapath_status = self._current_datapath_status_locked()
            self._observed_state = self._observed_from_datapath(
                datapath_status,
                topology_applied=False,
                effective_dpdk_config=None,
            )
            self._recompute_controller_health(datapath_status)
        return result

    def health_snapshot(self) -> ControllerHealthSnapshot:
        """Return the latest controller and datapath health view."""

        with self._lock:
            datapath_status = self._current_datapath_status_locked()
            if self._started and self._supervisor is not None:
                self._observed_state = self._observed_from_datapath(
                    datapath_status,
                    topology_applied=self._observed_state.topology_applied,
                    effective_dpdk_config=self._observed_state.effective_dpdk_config,
                )
                self._recompute_controller_health(datapath_status)

            return ControllerHealthSnapshot(
                controller_service="pktlab-ctrld",
                controller_version=__version__,
                controller_state=self._controller_state,
                controller_message=self._controller_message,
                desired_state=self._desired_state,
                observed_state=self._observed_state,
                datapath_status=datapath_status,
            )

    def _recompute_controller_health(self, datapath_status: DatapathProcessStatus) -> None:
        if self._controller_override_message is not None:
            self._controller_state = "degraded"
            self._controller_message = self._controller_override_message
            return

        if not self._started and self._controller_state == "stopped":
            self._controller_message = "controller is not started"
            return

        if not self.config.supervise_datapath:
            self._controller_state = "running"
            self._controller_message = "controller ready without datapath supervision"
            return

        if not self._desired_state.desired_datapath_running:
            if datapath_status.running:
                self._controller_state = "degraded"
                self._controller_message = "datapath process is running without an active topology"
                return
            self._controller_state = "running"
            self._controller_message = "controller ready without active topology"
            return

        if not datapath_status.running:
            self._controller_state = "degraded"
            self._controller_message = datapath_status.last_error or "datapath process is not running"
            return

        if not datapath_status.reachable or datapath_status.health is None:
            self._controller_state = "degraded"
            self._controller_message = datapath_status.last_error or "datapath IPC is not reachable"
            return

        if datapath_status.health.state == "running":
            self._controller_state = "running"
            self._controller_message = "controller ready"
            return

        self._controller_state = "degraded"
        self._controller_message = (
            f"datapath reported state {datapath_status.health.state}: {datapath_status.health.message}"
        )

    def _observed_from_datapath(
        self,
        datapath_status: DatapathProcessStatus,
        *,
        topology_applied: bool,
        effective_dpdk_config: EffectiveDpdkRuntimeModel | None,
    ) -> ObservedState:
        health = datapath_status.health
        return ObservedState(
            datapath_health=health.state if health is not None else None,
            applied_rules_version=health.applied_rule_version if health is not None else None,
            dpdkd_pid=datapath_status.pid,
            effective_dpdk_config=effective_dpdk_config,
            active_captures=self._observed_state.active_captures,
            topology_applied=topology_applied,
        )

    def _unmanaged_datapath_status(self) -> DatapathProcessStatus:
        return DatapathProcessStatus(
            managed=self.config.supervise_datapath,
            socket_path=self.config.datapath_socket_path,
        )

    def _current_datapath_status_locked(self) -> DatapathProcessStatus:
        datapath_status = self._unmanaged_datapath_status()
        if self._started and self._supervisor is not None:
            datapath_status = self._supervisor.status()
        return datapath_status

    def _desired_state_without_topology(self) -> DesiredState:
        return DesiredState(
            desired_controller_state="running" if self._started else "stopped",
            desired_datapath_running=False,
        )

    def _clear_controller_override(self) -> None:
        self._controller_override_message = None

    def _build_supervisor_config(
        self,
        *,
        namespace: str | None = None,
        extra_args: tuple[str, ...] = (),
    ) -> SupervisorConfig:
        launch_prefix: tuple[str, ...] = ()
        if namespace is not None:
            launch_prefix = ("ip", "netns", "exec", namespace)
        return SupervisorConfig(
            dpdkd_binary=self.config.datapath_binary,
            socket_path=self.config.datapath_socket_path,
            launch_prefix=launch_prefix,
            extra_args=extra_args,
            startup_timeout_seconds=self.config.datapath_startup_timeout_seconds,
        )

    def _start_topology_datapath(
        self,
        validated_topology: ValidatedTopologyConfig,
    ) -> DatapathProcessStatus:
        if not self.config.supervise_datapath:
            raise PktlabError(
                ErrorCode.STATE_CONFLICT,
                "controller was started without datapath supervision, so topology apply cannot launch pktlab-dpdkd",
            )

        with self._lock:
            if self._supervisor is not None:
                self._supervisor.stop()
            self._supervisor = DpdkdSupervisor(
                self._build_supervisor_config(
                    namespace=validated_topology.requested_dpdk_config.namespace,
                    extra_args=build_dpdk_runtime_args(validated_topology),
                )
            )
            return self._supervisor.start()

    def _stop_topology_datapath(self) -> None:
        with self._lock:
            if self._supervisor is not None:
                self._supervisor.stop()


def build_dpdk_runtime_args(validated_topology: ValidatedTopologyConfig) -> tuple[str, ...]:
    """Render datapath CLI arguments from the controller-validated runtime profile."""

    effective = validated_topology.effective_dpdk_config
    ingress_port_name = _port_name_for_role(validated_topology, "ingress")
    egress_port_name = _port_name_for_role(validated_topology, "egress")
    return (
        "--lcores",
        effective.lcores,
        "--hugepages-mb",
        str(effective.hugepages_mb),
        "--burst-size",
        str(effective.burst_size),
        "--rx-queue-size",
        str(effective.rx_queue_size),
        "--tx-queue-size",
        str(effective.tx_queue_size),
        "--mempool-size",
        str(effective.mempool_size),
        "--ingress-port-name",
        ingress_port_name,
        "--egress-port-name",
        egress_port_name,
    )


def _port_name_for_role(validated_topology: ValidatedTopologyConfig, role: str) -> str:
    for port in validated_topology.topology.dpdk_ports:
        if port.role == role:
            return port.name
    raise ValueError(f"expected a dpdk port with role {role}")


__all__ = [
    "ControllerConfig",
    "ControllerHealthSnapshot",
    "ControllerRuntime",
    "build_dpdk_runtime_args",
]
