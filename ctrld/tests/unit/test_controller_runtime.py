"""Unit tests for controller runtime state transitions."""

from __future__ import annotations

import unittest

from pktlab_ctrld.app import ControllerConfig, ControllerRuntime
from pktlab_ctrld.process.supervisor import DatapathProcessStatus
from pktlab_ctrld.topology.manager import TopologyOperationResult


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

    def set_status(self, status: DatapathProcessStatus) -> None:
        self._status = status


class FakeTopologyManager:
    """Minimal topology manager fake for controller runtime tests."""

    def __init__(self, *, destroy_result: TopologyOperationResult, has_applied_topology: bool = False) -> None:
        self._destroy_result = destroy_result
        self.has_applied_topology = has_applied_topology
        self.destroy_calls = 0

    def destroy(self) -> TopologyOperationResult:
        self.destroy_calls += 1
        self.has_applied_topology = False
        return self._destroy_result


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
