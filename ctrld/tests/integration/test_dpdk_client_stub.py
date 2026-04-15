"""Integration test for the Python datapath client against the C datapath daemon."""

from __future__ import annotations

import itertools
import pathlib
import subprocess
import tempfile
import time
import unittest

IMPORT_ERROR: ModuleNotFoundError | None = None

try:
    from pktlab_ctrld.dpdk_client.client import DpdkClient
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    if exc.name != "pydantic":
        raise
    IMPORT_ERROR = exc

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_DPDKD_BINARY = REPO_ROOT / "build" / "dpdkd" / "pktlab-dpdkd"


def wait_for_socket(socket_path: pathlib.Path, proc: subprocess.Popen[str]) -> None:
    """Wait until the subprocess creates its Unix socket or exits."""

    deadline = time.time() + 5.0
    while time.time() < deadline:
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            raise RuntimeError(f"dpdkd exited early with code {proc.returncode}: {stderr}")
        if socket_path.exists():
            return
        time.sleep(0.05)
    raise RuntimeError("timed out waiting for datapath socket")


@unittest.skipIf(IMPORT_ERROR is not None, "pydantic is not installed")
class DpdkClientStubIntegrationTests(unittest.TestCase):
    """Verify the Python client can speak to the C IPC stub."""

    def test_client_ping_version_and_health(self) -> None:
        if not DEFAULT_DPDKD_BINARY.exists():
            raise unittest.SkipTest(
                f"dpdkd stub binary is missing; build it first at {DEFAULT_DPDKD_BINARY}"
            )

        request_ids = itertools.count(1)

        with tempfile.TemporaryDirectory(prefix="pktlab-ctrld-") as tmpdir:
            socket_path = pathlib.Path(tmpdir) / "dpdkd.sock"
            proc = subprocess.Popen(
                [str(DEFAULT_DPDKD_BINARY), "--socket-path", str(socket_path)],
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
            )

            try:
                wait_for_socket(socket_path, proc)

                client = DpdkClient(
                    str(socket_path),
                    request_id_factory=lambda: f"req-it-{next(request_ids)}",
                )

                ping = client.ping()
                self.assertTrue(ping.ok)
                self.assertEqual(ping.request_id, "req-it-1")
                self.assertEqual(ping.unwrap().message, "pong")

                version = client.get_version()
                self.assertTrue(version.ok)
                self.assertEqual(version.request_id, "req-it-2")
                self.assertEqual(version.unwrap().service, "pktlab-dpdkd")

                health = client.get_health()
                self.assertTrue(health.ok)
                self.assertEqual(health.request_id, "req-it-3")
                health_state = health.unwrap().health
                self.assertIn(health_state.state, {"running", "degraded"})
                self.assertFalse(health_state.ports_ready)
                self.assertFalse(health_state.paused)
                if health_state.state == "degraded":
                    self.assertTrue(
                        any(
                            marker in health_state.message
                            for marker in ("need root/CAP_NET_ADMIN", "libdpdk not available")
                        )
                    )
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                if proc.stderr is not None:
                    proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
