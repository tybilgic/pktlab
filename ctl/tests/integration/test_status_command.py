"""Smoke test for `pktlabctl status` against a local controller process."""

from __future__ import annotations

import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import unittest

import httpx

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_DPDKD_BINARY = REPO_ROOT / "build" / "dpdkd" / "pktlab-dpdkd"


def reserve_tcp_port() -> int:
    """Reserve a localhost TCP port for the test server."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(url: str, proc: subprocess.Popen[str]) -> dict[str, object]:
    """Wait until the controller returns a successful health response."""

    deadline = time.time() + 10.0
    while time.time() < deadline:
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            raise RuntimeError(f"controller exited early with code {proc.returncode}: {stderr}")
        try:
            response = httpx.get(f"{url}/health", timeout=0.2)
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
        except httpx.HTTPError:
            pass
        time.sleep(0.05)
    raise RuntimeError("timed out waiting for controller health")


class StatusCommandIntegrationTests(unittest.TestCase):
    """Verify the CLI talks only to the controller API."""

    def test_status_command_supports_human_and_json_output(self) -> None:
        if not DEFAULT_DPDKD_BINARY.exists():
            raise unittest.SkipTest(
                f"dpdkd stub binary is missing; build it first at {DEFAULT_DPDKD_BINARY}"
            )

        port = reserve_tcp_port()
        controller_url = f"http://127.0.0.1:{port}"

        with tempfile.TemporaryDirectory(prefix="pktlabctl-status-") as tmpdir:
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
                        "status",
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(human.returncode, 0, msg=human.stderr)
                self.assertIn("controller: running", human.stdout)
                self.assertIn("datapath: reachable", human.stdout)

                json_result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pktlabctl.main",
                        "--controller-url",
                        controller_url,
                        "--json",
                        "status",
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
                payload = json.loads(json_result.stdout)
                self.assertEqual(payload["controller"]["state"], "running")
                self.assertTrue(payload["datapath"]["reachable"])
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
