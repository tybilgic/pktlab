#!/usr/bin/env python3
"""Opt-in privileged smoke test for real datapath forwarding."""

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


def bridge_exists(name: str) -> bool:
    return link_exists(name)


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
        "failed to reserve the required 2 MB hugepages for the privileged forwarding smoke test"
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


def main() -> int:
    if os.environ.get("PKTLAB_RUN_PRIVILEGED_DPDKD_FORWARDING_SMOKE") != "1":
        print(
            "skipping: set PKTLAB_RUN_PRIVILEGED_DPDKD_FORWARDING_SMOKE=1 "
            "to run the privileged datapath forwarding smoke test",
            file=sys.stderr,
        )
        return 0
    if os.geteuid() != 0:
        print("skipping: privileged datapath forwarding smoke test requires root", file=sys.stderr)
        return 0
    if shutil.which("ip") is None:
        print("skipping: privileged datapath forwarding smoke test requires the ip command", file=sys.stderr)
        return 0
    if shutil.which("ping") is None:
        print("skipping: privileged datapath forwarding smoke test requires the ping command", file=sys.stderr)
        return 0

    executable = pathlib.Path(sys.argv[1]).resolve()
    token = uuid.uuid4().hex[:4]
    ingress = "dtap0"
    egress = "dtap1"
    src_namespace = f"pktlab-fs-{token}"
    sink_namespace = f"pktlab-fk-{token}"
    ingress_bridge = f"pki{token}"
    egress_bridge = f"pko{token}"
    ingress_peer = f"vin{token}"
    egress_peer = f"vout{token}"
    hugepages_mb = 256
    reservation = reserve_hugepages(hugepages_mb)

    try:
        if any(
            (
                link_exists(ingress),
                link_exists(egress),
                bridge_exists(ingress_bridge),
                bridge_exists(egress_bridge),
                link_exists(ingress_peer),
                link_exists(egress_peer),
                namespace_exists(src_namespace),
                namespace_exists(sink_namespace),
            )
        ):
            raise RuntimeError("refusing to run forwarding smoke test because one of the test resources already exists")

        with tempfile.TemporaryDirectory(prefix="pktlab-dpdkd-forwarding-") as tmpdir:
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
                assert "forwarding loop active" in health_state["message"]

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
                run_command(["ip", "link", "add", "name", ingress_bridge, "type", "bridge"])
                run_command(["ip", "link", "add", "name", egress_bridge, "type", "bridge"])

                run_command(["ip", "-n", src_namespace, "link", "set", "dev", "lo", "up"])
                run_command(["ip", "-n", sink_namespace, "link", "set", "dev", "lo", "up"])
                run_command(["ip", "-n", src_namespace, "address", "replace", "10.0.0.1/24", "dev", "eth0"])
                run_command(["ip", "-n", sink_namespace, "address", "replace", "10.0.0.2/24", "dev", "eth0"])

                for bridge in (ingress_bridge, egress_bridge):
                    run_command(["ip", "link", "set", "dev", bridge, "up"])
                for interface in (ingress, egress, ingress_peer, egress_peer):
                    run_command(["ip", "link", "set", "dev", interface, "up"])
                for namespace in (src_namespace, sink_namespace):
                    run_command(["ip", "-n", namespace, "link", "set", "dev", "eth0", "up"])

                run_command(["ip", "link", "set", "dev", ingress_peer, "master", ingress_bridge])
                run_command(["ip", "link", "set", "dev", ingress, "master", ingress_bridge])
                run_command(["ip", "link", "set", "dev", egress_peer, "master", egress_bridge])
                run_command(["ip", "link", "set", "dev", egress, "master", egress_bridge])

                ping(src_namespace, "10.0.0.2")
                ping(sink_namespace, "10.0.0.1")
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                delete_link_if_present(ingress_bridge)
                delete_link_if_present(egress_bridge)
                delete_link_if_present(ingress_peer)
                delete_link_if_present(egress_peer)
                delete_namespace_if_present(src_namespace)
                delete_namespace_if_present(sink_namespace)
                delete_link_if_present(ingress)
                delete_link_if_present(egress)
    finally:
        restore_hugepages(reservation)

    print("ok: privileged datapath forwarding smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
