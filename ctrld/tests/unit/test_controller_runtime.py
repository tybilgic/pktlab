"""Unit tests for controller runtime state transitions."""

from __future__ import annotations

from dataclasses import dataclass
import unittest

from pktlab_ctrld.app import ControllerConfig, ControllerRuntime
from pktlab_ctrld.process.supervisor import DatapathProcessStatus
from pktlab_ctrld.topology.manager import TopologyOperationResult
from pktlab_ctrld.types import DpdkProcessConfigModel, EffectiveDpdkRuntimeModel


@dataclass(frozen=True, slots=True)
class ApplyOutcome:
    """Single fake topology-manager apply outcome."""

    value: TopologyOperationResult | Exception
    has_applied_topology: bool


class FakeSupervisor:
    """Minimal supervisor fake that lets tests control reported datapath status."""

    def __init__(self, *, status: DatapathProcessStatus) -> None:
        self._status = status
        self.start_calls = 0
        self.stop_calls = 0

    def start(self) -> DatapathProcessStatus:
        self.start_calls += 1
        return self._status

    def status(self) -> DatapathProcessStatus:
        return self._status

    def stop(self) -> None:
        self.stop_calls += 1
        self._status = DatapathProcessStatus(
            managed=self._status.managed,
            socket_path=self._status.socket_path,
        )

    def set_status(self, status: DatapathProcessStatus) -> None:
        self._status = status


class FakeTopologyManager:
    """Minimal topology manager fake for controller runtime tests."""

    def __init__(
        self,
        *,
        destroy_result: TopologyOperationResult,
        apply_outcomes: tuple[ApplyOutcome, ...] = (),
        has_applied_topology: bool = False,
    ) -> None:
        self._destroy_result = destroy_result
        self._apply_outcomes = list(apply_outcomes)
        self.has_applied_topology = has_applied_topology
        self.apply_calls: list[str] = []
        self.destroy_calls = 0

    def apply(self, config_path: str) -> TopologyOperationResult:
        self.apply_calls.append(config_path)
        if not self._apply_outcomes:
            raise AssertionError("unexpected topology apply in test")

        outcome = self._apply_outcomes.pop(0)
        self.has_applied_topology = outcome.has_applied_topology
        if isinstance(outcome.value, Exception):
            raise outcome.value
        return outcome.value

    def destroy(self) -> TopologyOperationResult:
        self.destroy_calls += 1
        self.has_applied_topology = False
        return self._destroy_result


def topology_apply_result(config_path: str) -> TopologyOperationResult:
    """Build a consistent topology-apply result for tests."""

    requested = DpdkProcessConfigModel(namespace="dpdk-host")
    effective = EffectiveDpdkRuntimeModel(
        lcores="1",
        lcore_count=1,
        hugepages_mb=256,
        burst_size=32,
        rx_queue_size=256,
        tx_queue_size=256,
        mempool_size=4096,
        port_count=2,
    )
    return TopologyOperationResult(
        operation="apply",
        topology_name="linear-basic",
        config_path=config_path,
        applied=True,
        datapath_namespace="dpdk-host",
        datapath_running=True,
        message="topology applied",
        requested_dpdk_config=requested,
        effective_dpdk_config=effective,
    )


def running_datapath_status() -> DatapathProcessStatus:
    """Return a healthy running datapath status for controller runtime tests."""

    from pktlab_ctrld.dpdk_client.models import HealthStateModel, VersionPayload

    return DatapathProcessStatus(
        managed=True,
        socket_path="/tmp/pktlab.sock",
        pid=1234,
        running=True,
        reachable=True,
        version=VersionPayload(
            service="pktlab-dpdkd",
            version="0.1.0",
            dpdk_version="25.11.0",
        ),
        health=HealthStateModel(
            state="running",
            message="ready",
            applied_rule_version=0,
            ports_ready=False,
            paused=False,
        ),
    )


class ControllerRuntimeTests(unittest.TestCase):
    """Keep controller health transitions aligned with desired state."""

    def test_failed_apply_clears_stale_topology_state_and_preserves_failure_message(self) -> None:
        supervisor = FakeSupervisor(status=running_datapath_status())
        topology_manager = FakeTopologyManager(
            destroy_result=TopologyOperationResult(
                operation="destroy",
                topology_name=None,
                config_path=None,
                applied=False,
                datapath_namespace=None,
                datapath_running=False,
                message="no topology is currently applied",
            ),
            apply_outcomes=(
                ApplyOutcome(
                    value=topology_apply_result("lab/topology.yaml"),
                    has_applied_topology=True,
                ),
                ApplyOutcome(
                    value=RuntimeError("tap reconciliation failed"),
                    has_applied_topology=False,
                ),
            ),
        )
        runtime = ControllerRuntime(
            ControllerConfig(
                datapath_binary="/bin/true",
                datapath_socket_path="/tmp/pktlab.sock",
            ),
            supervisor=supervisor,
            topology_manager=topology_manager,
        )

        runtime.start()
        runtime.apply_topology("lab/topology.yaml")
        supervisor.set_status(
            DatapathProcessStatus(
                managed=True,
                socket_path="/tmp/pktlab.sock",
            )
        )

        with self.assertRaises(RuntimeError):
            runtime.apply_topology("lab/new-topology.yaml")

        snapshot = runtime.health_snapshot()

        self.assertEqual(snapshot.controller_state, "degraded")
        self.assertEqual(snapshot.controller_message, "failed to apply topology from lab/new-topology.yaml")
        self.assertIsNone(snapshot.desired_state.topology_config_path)
        self.assertIsNone(snapshot.desired_state.topology_name)
        self.assertFalse(snapshot.desired_state.desired_datapath_running)
        self.assertFalse(snapshot.observed_state.topology_applied)
        self.assertIsNone(snapshot.observed_state.effective_dpdk_config)
        self.assertEqual(topology_manager.apply_calls, ["lab/topology.yaml", "lab/new-topology.yaml"])

    def test_destroy_topology_keeps_controller_running_when_no_datapath_is_desired(self) -> None:
        supervisor = FakeSupervisor(status=running_datapath_status())
        topology_manager = FakeTopologyManager(
            destroy_result=TopologyOperationResult(
                operation="destroy",
                topology_name="linear-basic",
                config_path="lab/topology.yaml",
                applied=False,
                datapath_namespace="dpdk-host",
                datapath_running=False,
                message="topology destroyed",
            )
        )
        runtime = ControllerRuntime(
            ControllerConfig(
                datapath_binary="/bin/true",
                datapath_socket_path="/tmp/pktlab.sock",
            ),
            supervisor=supervisor,
            topology_manager=topology_manager,
        )

        runtime.start()
        supervisor.set_status(
            DatapathProcessStatus(
                managed=True,
                socket_path="/tmp/pktlab.sock",
            )
        )

        result = runtime.destroy_topology()
        snapshot = runtime.health_snapshot()

        self.assertEqual(result.message, "topology destroyed")
        self.assertEqual(topology_manager.destroy_calls, 1)
        self.assertEqual(snapshot.controller_state, "running")
        self.assertEqual(snapshot.controller_message, "controller ready without active topology")
        self.assertFalse(snapshot.desired_state.desired_datapath_running)
        self.assertFalse(snapshot.datapath_status.running)

    def test_destroy_topology_stops_supervised_datapath_even_when_no_topology_is_applied(self) -> None:
        supervisor = FakeSupervisor(status=running_datapath_status())
        topology_manager = FakeTopologyManager(
            destroy_result=TopologyOperationResult(
                operation="destroy",
                topology_name=None,
                config_path=None,
                applied=False,
                datapath_namespace=None,
                datapath_running=False,
                message="no topology is currently applied",
            )
        )
        runtime = ControllerRuntime(
            ControllerConfig(
                datapath_binary="/bin/true",
                datapath_socket_path="/tmp/pktlab.sock",
            ),
            supervisor=supervisor,
            topology_manager=topology_manager,
        )

        runtime.start()

        result = runtime.destroy_topology()
        snapshot = runtime.health_snapshot()

        self.assertEqual(result.message, "no topology is currently applied")
        self.assertEqual(topology_manager.destroy_calls, 1)
        self.assertEqual(supervisor.stop_calls, 1)
        self.assertEqual(snapshot.controller_state, "running")
        self.assertEqual(snapshot.controller_message, "controller ready without active topology")
        self.assertFalse(snapshot.datapath_status.running)
        self.assertFalse(snapshot.desired_state.desired_datapath_running)

    def test_unexpected_running_datapath_without_active_topology_is_degraded(self) -> None:
        supervisor = FakeSupervisor(status=running_datapath_status())
        runtime = ControllerRuntime(
            ControllerConfig(
                datapath_binary="/bin/true",
                datapath_socket_path="/tmp/pktlab.sock",
            ),
            supervisor=supervisor,
            topology_manager=FakeTopologyManager(
                destroy_result=TopologyOperationResult(
                    operation="destroy",
                    topology_name="linear-basic",
                    config_path="lab/topology.yaml",
                    applied=False,
                    datapath_namespace="dpdk-host",
                    datapath_running=False,
                    message="topology destroyed",
                )
            ),
        )

        runtime.start()
        runtime.destroy_topology()
        supervisor.set_status(running_datapath_status())

        snapshot = runtime.health_snapshot()

        self.assertEqual(snapshot.controller_state, "degraded")
        self.assertEqual(
            snapshot.controller_message,
            "datapath process is running without an active topology",
        )


if __name__ == "__main__":
    unittest.main()
