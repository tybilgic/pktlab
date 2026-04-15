"""Integration tests for controller runtime visibility endpoints."""

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


def _is_expected_degraded_datapath_message(message: str) -> bool:
    return any(marker in message for marker in ("need root/CAP_NET_ADMIN", "libdpdk not available"))


class ControllerHealthApiIntegrationTests(unittest.TestCase):
    """Verify the controller supervises the datapath and exposes read-only status routes."""

    def test_health_and_datapath_endpoints_report_consistent_runtime_state(self) -> None:
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
                datapath_state = payload["datapath"]["state"]
                self.assertEqual(payload["controller"]["service"], "pktlab-ctrld")
                self.assertEqual(payload["datapath"]["service"], "pktlab-dpdkd")
                self.assertTrue(payload["datapath"]["managed"])
                self.assertTrue(payload["datapath"]["reachable"])
                self.assertIn(datapath_state, {"running", "degraded"})
                self.assertFalse(payload["datapath"]["ports_ready"])
                self.assertFalse(payload["datapath"]["paused"])
                if datapath_state == "running":
                    self.assertEqual(payload["controller"]["state"], "running")
                else:
                    self.assertEqual(payload["controller"]["state"], "degraded")
                    self.assertTrue(_is_expected_degraded_datapath_message(payload["datapath"]["message"]))

                status_response = client.get("/datapath/status")
                self.assertEqual(status_response.status_code, 200)
                status_payload = status_response.json()
                self.assertEqual(status_payload["controller"]["state"], payload["controller"]["state"])
                self.assertEqual(status_payload["datapath"]["state"], payload["datapath"]["state"])
                self.assertEqual(
                    [port["name"] for port in status_payload["ports"]],
                    ["dtap0", "dtap1"],
                )
                self.assertEqual(
                    [port["role"] for port in status_payload["ports"]],
                    ["ingress", "egress"],
                )

                stats_response = client.get("/datapath/stats")
                self.assertEqual(stats_response.status_code, 200)
                stats_payload = stats_response.json()
                self.assertEqual(stats_payload["datapath"]["state"], payload["datapath"]["state"])
                self.assertEqual(stats_payload["stats"]["rx_packets"], 0)
                self.assertEqual(stats_payload["stats"]["tx_packets"], 0)
                self.assertEqual(stats_payload["stats"]["drop_packets"], 0)
                self.assertEqual(stats_payload["stats"]["rule_hits"], {})


if __name__ == "__main__":
    unittest.main()
