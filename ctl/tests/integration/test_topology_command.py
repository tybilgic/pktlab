"""Smoke test for `pktlabctl topology ...` against a small local HTTP stub."""

from __future__ import annotations

import json
import pathlib
import socket
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def reserve_tcp_port() -> int:
    """Reserve a localhost TCP port for the test server."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _TopologyHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length) or b"{}")

        if self.path == "/topology/apply":
            body = {
                "operation": "apply",
                "topology_name": "linear-basic",
                "config_path": payload["config_path"],
                "applied": True,
                "datapath_namespace": "dpdk-host",
                "datapath_running": True,
                "message": "topology applied",
            }
        elif self.path == "/topology/destroy":
            body = {
                "operation": "destroy",
                "topology_name": "linear-basic",
                "config_path": "lab/topology.yaml",
                "applied": False,
                "datapath_namespace": "dpdk-host",
                "datapath_running": False,
                "message": "topology destroyed",
            }
        else:  # pragma: no cover - defensive guard
            self.send_response(404)
            self.end_headers()
            return

        encoded = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


class TopologyCommandIntegrationTests(unittest.TestCase):
    """Verify the CLI topology commands talk to the controller API surface."""

    def test_topology_apply_and_destroy_commands(self) -> None:
        port = reserve_tcp_port()
        server = ThreadingHTTPServer(("127.0.0.1", port), _TopologyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        controller_url = f"http://127.0.0.1:{port}"

        try:
            apply_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pktlabctl.main",
                    "--controller-url",
                    controller_url,
                    "topology",
                    "apply",
                    "-f",
                    "lab/topology.yaml",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(apply_result.returncode, 0, msg=apply_result.stderr)
            self.assertIn("topology apply: topology applied", apply_result.stdout)
            self.assertIn("datapath_namespace: dpdk-host", apply_result.stdout)

            destroy_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pktlabctl.main",
                    "--controller-url",
                    controller_url,
                    "--json",
                    "topology",
                    "destroy",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(destroy_result.returncode, 0, msg=destroy_result.stderr)
            payload = json.loads(destroy_result.stdout)
            self.assertEqual(payload["operation"], "destroy")
            self.assertFalse(payload["applied"])
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
