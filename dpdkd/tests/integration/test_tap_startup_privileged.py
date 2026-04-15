#!/usr/bin/env python3
"""Opt-in privileged smoke test for real DPDK TAP startup."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass


HUGEPAGE_SIZE_MB = 2
HUGEPAGE_SYSFS_DIR = pathlib.Path("/sys/kernel/mm/hugepages/hugepages-2048kB")


@dataclass
class HugepageReservation:
    original_total_pages: int
    modified: bool


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


def link_exists(name: str) -> bool:
    return subprocess.run(
        ["ip", "link", "show", "dev", name],
        check=False,
        capture_output=True,
        text=True,
    ).returncode == 0


def delete_link_if_present(name: str) -> None:
    if link_exists(name):
        subprocess.run(
            ["ip", "link", "delete", "dev", name],
            check=True,
            capture_output=True,
            text=True,
        )


def read_int_file(path: pathlib.Path) -> int:
    return int(path.read_text(encoding="utf-8").strip())


def write_int_file(path: pathlib.Path, value: int) -> None:
    path.write_text(f"{value}\n", encoding="utf-8")


def reserve_hugepages(required_mb: int) -> HugepageReservation:
    nr_hugepages_path = HUGEPAGE_SYSFS_DIR / "nr_hugepages"
    free_hugepages_path = HUGEPAGE_SYSFS_DIR / "free_hugepages"
    required_pages = required_mb // HUGEPAGE_SIZE_MB
    original_total_pages = read_int_file(nr_hugepages_path)
    free_pages = read_int_file(free_hugepages_path)
    target_total_pages = original_total_pages

    if free_pages >= required_pages:
        return HugepageReservation(original_total_pages=original_total_pages, modified=False)

    target_total_pages = original_total_pages + (required_pages - free_pages)
    write_int_file(nr_hugepages_path, target_total_pages)

    deadline = time.time() + 5.0
    while time.time() < deadline:
        current_total_pages = read_int_file(nr_hugepages_path)
        current_free_pages = read_int_file(free_hugepages_path)
        if current_total_pages >= target_total_pages and current_free_pages >= required_pages:
            return HugepageReservation(original_total_pages=original_total_pages, modified=True)
        time.sleep(0.05)

    raise RuntimeError(
        "failed to reserve the required 2 MB hugepages for the privileged datapath smoke test"
    )


def restore_hugepages(reservation: HugepageReservation) -> None:
    nr_hugepages_path = HUGEPAGE_SYSFS_DIR / "nr_hugepages"

    if not reservation.modified:
        return

    write_int_file(nr_hugepages_path, reservation.original_total_pages)


def main() -> int:
    if os.environ.get("PKTLAB_RUN_PRIVILEGED_DPDKD_SMOKE") != "1":
        print(
            "skipping: set PKTLAB_RUN_PRIVILEGED_DPDKD_SMOKE=1 to run the privileged datapath smoke test",
            file=sys.stderr,
        )
        return 0
    if os.geteuid() != 0:
        print("skipping: privileged datapath smoke test requires root or CAP_NET_ADMIN", file=sys.stderr)
        return 0
    if shutil.which("ip") is None:
        print("skipping: privileged datapath smoke test requires the ip command", file=sys.stderr)
        return 0

    executable = pathlib.Path(sys.argv[1]).resolve()
    ingress = "dtap0"
    egress = "dtap1"
    hugepages_mb = 256
    reservation = reserve_hugepages(hugepages_mb)

    try:
        if link_exists(ingress) or link_exists(egress):
            raise RuntimeError("refusing to run privileged datapath smoke test because dtap0/dtap1 already exist")

        with tempfile.TemporaryDirectory(prefix="pktlab-dpdkd-") as tmpdir:
            socket_path = pathlib.Path(tmpdir) / "dpdkd.sock"
            proc = subprocess.Popen(
                [
                    str(executable),
                    "--socket-path",
                    str(socket_path),
                    "--lcores",
                    "1",
                    "--hugepages-mb",
                    str(hugepages_mb),
                    "--burst-size",
                    "32",
                    "--rx-queue-size",
                    "256",
                    "--tx-queue-size",
                    "256",
                    "--mempool-size",
                    "4096",
                    "--ingress-port-name",
                    ingress,
                    "--egress-port-name",
                    egress,
                ],
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
            )

            try:
                wait_for_socket(socket_path, proc)

                health = send_request(
                    socket_path,
                    json.dumps({"id": "req-1", "cmd": "get_health", "payload": {}}).encode("utf-8"),
                )
                assert health["ok"] is True
                health_state = health["payload"]["health"]
                assert health_state["state"] == "running"
                assert health_state["ports_ready"] is True
                assert health_state["paused"] is False
                assert "dtap0/dtap1" in health_state["message"]
                assert "ready" in health_state["message"]
                assert link_exists(ingress)
                assert link_exists(egress)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                delete_link_if_present(ingress)
                delete_link_if_present(egress)
    finally:
        restore_hugepages(reservation)

    print("ok: privileged datapath TAP startup smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
