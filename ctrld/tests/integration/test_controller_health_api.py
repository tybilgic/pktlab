"""Integration test for controller startup and the `/health` endpoint."""

from __future__ import annotations

import pathlib
import tempfile
import time
import unittest

from fastapi.testclient import TestClient

from pktlab_ctrld.api.app import create_api_app
from pktlab_ctrld.app import ControllerConfig, ControllerRuntime

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_DPDKD_BINARY = REPO_ROOT / "build" / "dpdkd" / "pktlab-dpdkd"


class ControllerHealthApiIntegrationTests(unittest.TestCase):
    """Verify the controller supervises the datapath and exposes `/health`."""

    def test_health_endpoint_reports_running_controller_and_datapath(self) -> None:
        if not DEFAULT_DPDKD_BINARY.exists():
            raise unittest.SkipTest(
                f"dpdkd stub binary is missing; build it first at {DEFAULT_DPDKD_BINARY}"
            )

        with tempfile.TemporaryDirectory(prefix="pktlab-ctrld-api-") as tmpdir:
            socket_path = pathlib.Path(tmpdir) / "dpdkd.sock"
            controller = ControllerRuntime(
                ControllerConfig(
                    datapath_binary=str(DEFAULT_DPDKD_BINARY),
                    datapath_socket_path=str(socket_path),
                )
            )

            with TestClient(create_api_app(controller)) as client:
                deadline = time.time() + 5.0
                response = None
                while time.time() < deadline:
                    response = client.get("/health")
                    if response.status_code == 200:
                        break
                    time.sleep(0.05)

                self.assertIsNotNone(response)
                self.assertEqual(response.status_code, 200)

                payload = response.json()
                self.assertEqual(payload["controller"]["service"], "pktlab-ctrld")
                self.assertEqual(payload["controller"]["state"], "running")
                self.assertEqual(payload["datapath"]["service"], "pktlab-dpdkd")
                self.assertTrue(payload["datapath"]["managed"])
                self.assertTrue(payload["datapath"]["reachable"])
                self.assertEqual(payload["datapath"]["state"], "running")
                self.assertFalse(payload["datapath"]["ports_ready"])
                self.assertFalse(payload["datapath"]["paused"])


if __name__ == "__main__":
    unittest.main()
