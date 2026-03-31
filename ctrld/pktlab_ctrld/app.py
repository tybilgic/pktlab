"""Controller runtime state and service composition."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from pktlab_ctrld import __version__
from pktlab_ctrld.process.supervisor import DatapathProcessStatus, DpdkdSupervisor, SupervisorConfig
from pktlab_ctrld.state.desired import ControllerStateValue, DesiredState
from pktlab_ctrld.state.observed import ObservedState


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
        self._started = False
        self._supervisor = supervisor
        if self._supervisor is None and config.supervise_datapath:
            self._supervisor = DpdkdSupervisor(
                SupervisorConfig(
                    dpdkd_binary=config.datapath_binary,
                    socket_path=config.datapath_socket_path,
                    startup_timeout_seconds=config.datapath_startup_timeout_seconds,
                )
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

            self._controller_state = "starting"
            self._controller_message = "starting controller runtime"
            self._desired_state = DesiredState(
                desired_controller_state="running",
                desired_datapath_running=self.config.supervise_datapath,
            )

            datapath_status = self._unmanaged_datapath_status()
            if self._supervisor is not None:
                datapath_status = self._supervisor.start()

            self._observed_state = self._observed_from_datapath(datapath_status)
            self._started = True
            self._recompute_controller_health(datapath_status)

    def stop(self) -> None:
        """Stop controller-managed services."""

        with self._lock:
            if not self._started:
                return

            self._controller_state = "stopping"
            self._controller_message = "stopping controller runtime"

            if self._supervisor is not None:
                self._supervisor.stop()

            self._observed_state = self._observed_from_datapath(self._unmanaged_datapath_status())
            self._desired_state = DesiredState(
                desired_controller_state="stopped",
                desired_datapath_running=False,
            )
            self._controller_state = "stopped"
            self._controller_message = "controller stopped"
            self._started = False

    def health_snapshot(self) -> ControllerHealthSnapshot:
        """Return the latest controller and datapath health view."""

        with self._lock:
            datapath_status = self._unmanaged_datapath_status()
            if self._started and self._supervisor is not None:
                datapath_status = self._supervisor.status()
                self._observed_state = self._observed_from_datapath(datapath_status)
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
        if not self._started and self._controller_state == "stopped":
            self._controller_message = "controller is not started"
            return

        if not self.config.supervise_datapath:
            self._controller_state = "running"
            self._controller_message = "controller ready without datapath supervision"
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

    def _observed_from_datapath(self, datapath_status: DatapathProcessStatus) -> ObservedState:
        health = datapath_status.health
        return ObservedState(
            datapath_health=health.state if health is not None else None,
            applied_rules_version=health.applied_rule_version if health is not None else None,
            dpdkd_pid=datapath_status.pid,
            active_captures=self._observed_state.active_captures,
            topology_applied=self._observed_state.topology_applied,
        )

    def _unmanaged_datapath_status(self) -> DatapathProcessStatus:
        return DatapathProcessStatus(
            managed=self.config.supervise_datapath,
            socket_path=self.config.datapath_socket_path,
        )


__all__ = ["ControllerConfig", "ControllerHealthSnapshot", "ControllerRuntime"]
