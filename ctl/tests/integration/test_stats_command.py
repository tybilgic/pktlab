"""Smoke test for `pktlabctl stats show` against a local controller process."""

from __future__ import annotations

import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import unittest

from .test_status_command import DEFAULT_DPDKD_BINARY, REPO_ROOT, wait_for_health


def reserve_tcp_port() -> int:
    """Reserve a localhost TCP port for the test server."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class StatsCommandIntegrationTests(unittest.TestCase):
    """Verify the stats command talks only to the controller API surface."""

    def test_stats_show_and_reset_support_human_and_json_output(self) -> None:
        if not DEFAULT_DPDKD_BINARY.exists():
            raise unittest.SkipTest(
                f"dpdkd stub binary is missing; build it first at {DEFAULT_DPDKD_BINARY}"
            )

        port = reserve_tcp_port()
        controller_url = f"http://127.0.0.1:{port}"

        with tempfile.TemporaryDirectory(prefix="pktlabctl-stats-") as tmpdir:
            socket_path = pathlib.Path(tmpdir) / "dpdkd.sock"
            controller = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "pktlab_ctrld.main",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--dpdkd-bin",
                    str(DEFAULT_DPDKD_BINARY),
                    "--dpdkd-socket-path",
                    str(socket_path),
                    "--log-level",
                    "error",
                ],
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
            )

            try:
                wait_for_health(controller_url, controller)

                human = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pktlabctl.main",
                        "--controller-url",
                        controller_url,
                        "stats",
                        "show",
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(human.returncode, 0, msg=human.stderr)
                self.assertIn("datapath stats:", human.stdout)
                self.assertIn("rx_packets:", human.stdout)
                self.assertIn("rule_hits: none", human.stdout)

                json_result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pktlabctl.main",
                        "--controller-url",
                        controller_url,
                        "--json",
                        "stats",
                        "show",
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
                payload = json.loads(json_result.stdout)
                self.assertIn(payload["datapath"]["state"], {"running", "degraded"})
                self.assertEqual(payload["stats"]["rx_packets"], 0)
                self.assertEqual(payload["stats"]["rule_hits"], {})

                reset_human = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pktlabctl.main",
                        "--controller-url",
                        controller_url,
                        "stats",
                        "reset",
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(reset_human.returncode, 0, msg=reset_human.stderr)
                self.assertIn("datapath stats reset:", reset_human.stdout)
                self.assertIn("post-reset counters:", reset_human.stdout)
                self.assertIn("rx_packets: 0", reset_human.stdout)

                reset_json = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pktlabctl.main",
                        "--controller-url",
                        controller_url,
                        "--json",
                        "stats",
                        "reset",
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(reset_json.returncode, 0, msg=reset_json.stderr)
                reset_payload = json.loads(reset_json.stdout)
                self.assertEqual(reset_payload["message"], "datapath counters reset")
                self.assertEqual(reset_payload["stats"]["rx_packets"], 0)
                self.assertEqual(reset_payload["stats"]["rule_hits"], {})
            finally:
                controller.terminate()
                try:
                    controller.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    controller.kill()
                    controller.wait(timeout=5)
                if controller.stderr is not None:
                    controller.stderr.close()


if __name__ == "__main__":
    unittest.main()
