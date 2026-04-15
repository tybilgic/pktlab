"""Smoke test for `pktlabctl datapath ...` against a local controller process."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest

from .test_status_command import DEFAULT_DPDKD_BINARY, REPO_ROOT, reserve_tcp_port, wait_for_health


class DatapathCommandIntegrationTests(unittest.TestCase):
    """Verify datapath control commands go through the controller API."""

    def test_datapath_pause_and_resume_surface_controller_errors(self) -> None:
        if not DEFAULT_DPDKD_BINARY.exists():
            raise unittest.SkipTest(
                f"dpdkd stub binary is missing; build it first at {DEFAULT_DPDKD_BINARY}"
            )

        port = reserve_tcp_port()
        controller_url = f"http://127.0.0.1:{port}"

        with tempfile.TemporaryDirectory(prefix="pktlabctl-datapath-") as tmpdir:
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

                pause = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pktlabctl.main",
                        "--controller-url",
                        controller_url,
                        "datapath",
                        "pause",
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(pause.returncode, 1)
                self.assertEqual(pause.stdout, "")
                self.assertIn("HTTP 409", pause.stderr)
                self.assertIn("datapath forwarding loop is not active", pause.stderr)

                resume = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pktlabctl.main",
                        "--controller-url",
                        controller_url,
                        "datapath",
                        "resume",
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(resume.returncode, 1)
                self.assertEqual(resume.stdout, "")
                self.assertIn("HTTP 409", resume.stderr)
                self.assertIn("datapath forwarding loop is not active", resume.stderr)
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
