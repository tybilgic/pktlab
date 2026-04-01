"""Integration test for topology apply/destroy API routes with a fake controller."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from pktlab_ctrld.api.app import create_api_app
from pktlab_ctrld.app import ControllerHealthSnapshot
from pktlab_ctrld.process.supervisor import DatapathProcessStatus
from pktlab_ctrld.state.desired import DesiredState
from pktlab_ctrld.state.observed import ObservedState
from pktlab_ctrld.topology.manager import TopologyOperationResult


class FakeController:
    """Small fake that satisfies the API app contract for topology route tests."""

    def __init__(self) -> None:
        self.started = False
        self.applied_paths: list[str] = []
        self.destroy_count = 0

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def health_snapshot(self) -> ControllerHealthSnapshot:
        return ControllerHealthSnapshot(
            controller_service="pktlab-ctrld",
            controller_version="0.1.0",
            controller_state="running",
            controller_message="controller ready",
            desired_state=DesiredState(desired_controller_state="running"),
            observed_state=ObservedState(),
            datapath_status=DatapathProcessStatus(managed=False, socket_path="/tmp/pktlab.sock"),
        )

    def apply_topology(self, config_path: str) -> TopologyOperationResult:
        self.applied_paths.append(config_path)
        return TopologyOperationResult(
            operation="apply",
            topology_name="linear-basic",
            config_path=config_path,
            applied=True,
            datapath_namespace="dpdk-host",
            datapath_running=True,
            message="topology applied",
        )

    def destroy_topology(self) -> TopologyOperationResult:
        self.destroy_count += 1
        return TopologyOperationResult(
            operation="destroy",
            topology_name="linear-basic",
            config_path="lab/topology.yaml",
            applied=False,
            datapath_namespace="dpdk-host",
            datapath_running=False,
            message="topology destroyed",
        )


class TopologyApiIntegrationTests(unittest.TestCase):
    """Verify the topology routes are exposed and serialize the manager results."""

    def test_apply_and_destroy_routes_return_typed_payloads(self) -> None:
        controller = FakeController()

        with TestClient(create_api_app(controller)) as client:
            apply_response = client.post("/topology/apply", json={"config_path": "lab/topology.yaml"})
            destroy_response = client.post("/topology/destroy", json={})

        self.assertEqual(apply_response.status_code, 200)
        self.assertEqual(destroy_response.status_code, 200)
        self.assertEqual(controller.applied_paths, ["lab/topology.yaml"])
        self.assertEqual(controller.destroy_count, 1)
        self.assertEqual(apply_response.json()["operation"], "apply")
        self.assertEqual(destroy_response.json()["operation"], "destroy")


if __name__ == "__main__":
    unittest.main()
