#!/usr/bin/env python3
"""Smoke test for the dpdkd IPC stub."""

from __future__ import annotations

import json
import pathlib
import socket
import struct
import subprocess
import sys
import tempfile
import time


def read_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("unexpected EOF while reading from socket")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_request(socket_path: pathlib.Path, payload: bytes) -> dict[str, object]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(socket_path))
        client.sendall(struct.pack(">I", len(payload)) + payload)
        response_len = struct.unpack(">I", read_exact(client, 4))[0]
        response = read_exact(client, response_len)
    return json.loads(response.decode("utf-8"))


def wait_for_socket(socket_path: pathlib.Path, proc: subprocess.Popen[str]) -> None:
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            raise RuntimeError(f"dpdkd exited early with code {proc.returncode}: {stderr}")
        if socket_path.exists():
            return
        time.sleep(0.05)
    raise RuntimeError("timed out waiting for datapath socket")


def main() -> int:
    executable = pathlib.Path(sys.argv[1]).resolve()

    with tempfile.TemporaryDirectory(prefix="pktlab-dpdkd-") as tmpdir:
        socket_path = pathlib.Path(tmpdir) / "dpdkd.sock"
        proc = subprocess.Popen(
            [str(executable), "--socket-path", str(socket_path)],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
        )

        try:
            wait_for_socket(socket_path, proc)

            ping = send_request(
                socket_path,
                json.dumps({"id": "req-1", "cmd": "ping", "payload": {}}).encode("utf-8"),
            )
            assert ping == {"id": "req-1", "ok": True, "payload": {"message": "pong"}}

            version = send_request(
                socket_path,
                json.dumps({"id": "req-2", "cmd": "get_version", "payload": {}}).encode("utf-8"),
            )
            assert version["ok"] is True
            assert version["payload"]["service"] == "pktlab-dpdkd"
            assert version["payload"]["version"] == "0.1.0"

            health = send_request(
                socket_path,
                json.dumps({"id": "req-3", "cmd": "get_health", "payload": {}}).encode("utf-8"),
            )
            assert health["ok"] is True
            assert health["payload"]["health"]["state"] == "running"
            assert health["payload"]["health"]["ports_ready"] is False
            assert health["payload"]["health"]["paused"] is False

            unknown = send_request(
                socket_path,
                json.dumps({"id": "req-4", "cmd": "get_stats", "payload": {}}).encode("utf-8"),
            )
            assert unknown["ok"] is False
            assert unknown["error"]["code"] == "UNKNOWN_COMMAND"
            assert unknown["id"] == "req-4"

            malformed = send_request(
                socket_path,
                b'{"id":"req-5","cmd":"ping","payload":',
            )
            assert malformed["ok"] is False
            assert malformed["error"]["code"] == "INVALID_REQUEST"

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
