#!/usr/bin/env python3
"""Opt-in privileged smoke test for datapath pause and resume semantics."""

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
import uuid
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


def run_command(argv: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(argv, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(argv)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def link_exists(name: str, *, namespace: str | None = None) -> bool:
    argv = ["ip"]
    if namespace is not None:
        argv.extend(["-n", namespace])
    argv.extend(["link", "show", "dev", name])
    return subprocess.run(argv, check=False, capture_output=True, text=True).returncode == 0


def namespace_exists(name: str) -> bool:
    completed = subprocess.run(
        ["ip", "netns", "list"],
        check=False,
        capture_output=True,
        text=True,
    )
    return any(line.split()[0] == name for line in completed.stdout.splitlines() if line.split())


def delete_link_if_present(name: str, *, namespace: str | None = None) -> None:
    if not link_exists(name, namespace=namespace):
        return
    argv = ["ip"]
    if namespace is not None:
        argv.extend(["-n", namespace])
    argv.extend(["link", "delete", "dev", name])
    run_command(argv)


def delete_namespace_if_present(name: str) -> None:
    if not namespace_exists(name):
        return
    run_command(["ip", "netns", "delete", name])


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
        "failed to reserve the required 2 MB hugepages for the privileged pause/resume smoke test"
    )


def restore_hugepages(reservation: HugepageReservation) -> None:
    nr_hugepages_path = HUGEPAGE_SYSFS_DIR / "nr_hugepages"

    if not reservation.modified:
        return

    write_int_file(nr_hugepages_path, reservation.original_total_pages)


def ping(namespace: str, destination: str) -> None:
    run_command(
        [
            "ip",
            "netns",
            "exec",
            namespace,
            "ping",
            "-n",
            "-c",
            "1",
            "-W",
            "2",
            destination,
        ]
    )


def ping_fails(namespace: str, destination: str) -> bool:
    completed = subprocess.run(
        [
            "ip",
            "netns",
            "exec",
            namespace,
            "ping",
            "-n",
            "-c",
            "1",
            "-W",
            "1",
            destination,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode != 0


def wait_for_health_state(socket_path: pathlib.Path, *, expected_state: str, paused: bool) -> None:
    deadline = time.time() + 5.0
    while time.time() < deadline:
        health = send_request(
            socket_path,
            json.dumps({"id": "req-health", "cmd": "get_health", "payload": {}}).encode("utf-8"),
        )
        if health["ok"] is True:
            current = health["payload"]["health"]
            if current["state"] == expected_state and current["paused"] is paused:
                return
        time.sleep(0.05)
    raise RuntimeError(f"timed out waiting for health state {expected_state} paused={paused}")


def wait_for_ping_failure(namespace: str, destination: str) -> None:
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if ping_fails(namespace, destination):
            return
        time.sleep(0.1)
    raise RuntimeError("expected forwarding to stop while paused, but ping kept succeeding")


def main() -> int:
    if os.environ.get("PKTLAB_RUN_PRIVILEGED_DPDKD_PAUSE_SMOKE") != "1":
        print(
            "skipping: set PKTLAB_RUN_PRIVILEGED_DPDKD_PAUSE_SMOKE=1 "
            "to run the privileged datapath pause/resume smoke test",
            file=sys.stderr,
        )
        return 0
    if os.geteuid() != 0:
        print("skipping: privileged datapath pause/resume smoke test requires root", file=sys.stderr)
        return 0
    if shutil.which("ip") is None:
        print("skipping: privileged datapath pause/resume smoke test requires the ip command", file=sys.stderr)
        return 0
    if shutil.which("ping") is None:
        print("skipping: privileged datapath pause/resume smoke test requires the ping command", file=sys.stderr)
        return 0

    executable = pathlib.Path(sys.argv[1]).resolve()
    token = uuid.uuid4().hex[:4]
    ingress = "dtap0"
    egress = "dtap1"
    src_namespace = f"pktlab-ps-{token}"
    sink_namespace = f"pktlab-pk-{token}"
    ingress_bridge = f"ppi{token}"
    egress_bridge = f"ppo{token}"
    ingress_peer = f"pvin{token}"
    egress_peer = f"pvout{token}"
    hugepages_mb = 256
    reservation = reserve_hugepages(hugepages_mb)

    try:
        if any(
            (
                link_exists(ingress),
                link_exists(egress),
                link_exists(ingress_bridge),
                link_exists(egress_bridge),
                link_exists(ingress_peer),
                link_exists(egress_peer),
                namespace_exists(src_namespace),
                namespace_exists(sink_namespace),
            )
        ):
            raise RuntimeError("refusing to run pause/resume smoke test because one of the test resources already exists")

        with tempfile.TemporaryDirectory(prefix="pktlab-dpdkd-pause-") as tmpdir:
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
                wait_for_health_state(socket_path, expected_state="running", paused=False)

                run_command(["ip", "netns", "add", src_namespace])
                run_command(["ip", "netns", "add", sink_namespace])
                run_command(
                    [
                        "ip",
                        "link",
                        "add",
                        "name",
                        "eth0",
                        "netns",
                        src_namespace,
                        "type",
                        "veth",
                        "peer",
                        "name",
                        ingress_peer,
                    ]
                )
                run_command(
                    [
                        "ip",
                        "link",
                        "add",
                        "name",
                        "eth0",
                        "netns",
                        sink_namespace,
                        "type",
                        "veth",
                        "peer",
                        "name",
                        egress_peer,
                    ]
                )
                run_command(["ip", "link", "add", ingress_bridge, "type", "bridge"])
                run_command(["ip", "link", "add", egress_bridge, "type", "bridge"])
                run_command(["ip", "link", "set", ingress_peer, "master", ingress_bridge])
                run_command(["ip", "link", "set", egress_peer, "master", egress_bridge])
                run_command(["ip", "link", "set", ingress, "master", ingress_bridge])
                run_command(["ip", "link", "set", egress, "master", egress_bridge])
                run_command(["ip", "link", "set", ingress_bridge, "up"])
                run_command(["ip", "link", "set", egress_bridge, "up"])
                run_command(["ip", "link", "set", ingress_peer, "up"])
                run_command(["ip", "link", "set", egress_peer, "up"])
                run_command(["ip", "-n", src_namespace, "addr", "add", "10.10.0.1/24", "dev", "eth0"])
                run_command(["ip", "-n", sink_namespace, "addr", "add", "10.10.0.2/24", "dev", "eth0"])
                run_command(["ip", "-n", src_namespace, "link", "set", "lo", "up"])
                run_command(["ip", "-n", sink_namespace, "link", "set", "lo", "up"])
                run_command(["ip", "-n", src_namespace, "link", "set", "eth0", "up"])
                run_command(["ip", "-n", sink_namespace, "link", "set", "eth0", "up"])

                ping(src_namespace, "10.10.0.2")

                pause = send_request(
                    socket_path,
                    json.dumps({"id": "req-1", "cmd": "pause_datapath", "payload": {}}).encode("utf-8"),
                )
                assert pause == {
                    "id": "req-1",
                    "ok": True,
                    "payload": {"message": "datapath forwarding loop paused"},
                }
                wait_for_health_state(socket_path, expected_state="paused", paused=True)
                wait_for_ping_failure(src_namespace, "10.10.0.2")

                resume = send_request(
                    socket_path,
                    json.dumps({"id": "req-2", "cmd": "resume_datapath", "payload": {}}).encode("utf-8"),
                )
                assert resume == {
                    "id": "req-2",
                    "ok": True,
                    "payload": {"message": "datapath forwarding loop resumed"},
                }
                wait_for_health_state(socket_path, expected_state="running", paused=False)
                ping(src_namespace, "10.10.0.2")
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                delete_link_if_present(ingress)
                delete_link_if_present(egress)
                delete_link_if_present(ingress_bridge)
                delete_link_if_present(egress_bridge)
                delete_link_if_present(ingress_peer)
                delete_link_if_present(egress_peer)
                delete_namespace_if_present(src_namespace)
                delete_namespace_if_present(sink_namespace)
    finally:
        restore_hugepages(reservation)

    print("ok: privileged datapath pause/resume smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
