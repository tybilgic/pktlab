"""Opt-in privileged smoke test for controller-driven topology apply plus traffic."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
import uuid
from dataclasses import dataclass

from pktlab_ctrld.app import ControllerConfig, ControllerRuntime
from pktlab_ctrld.config.topology import load_topology_config
from pktlab_ctrld.config.validation import validate_topology_config
from pktlab_ctrld.util.netns import NetnsRunner

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_DPDKD_BINARY = REPO_ROOT / "build" / "dpdkd" / "pktlab-dpdkd"
DEFAULT_DPDKD_BINARY_ENV = "PKTLAB_DPDKD_BINARY"
HUGEPAGE_SIZE_MB = 2
HUGEPAGE_SYSFS_DIR = pathlib.Path("/sys/kernel/mm/hugepages/hugepages-2048kB")


@dataclass(frozen=True, slots=True)
class HugepageReservation:
    """Original host hugepage state for restoration after the smoke run."""

    original_total_pages: int
    modified: bool


def run_command(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a host command and raise a readable error on failure."""

    completed = subprocess.run(argv, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(argv)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def ping(namespace: str, destination: str) -> None:
    """Ping once inside a namespace."""

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


def read_int_file(path: pathlib.Path) -> int:
    """Read a sysfs integer file."""

    return int(path.read_text(encoding="utf-8").strip())


def write_int_file(path: pathlib.Path, value: int) -> None:
    """Write a sysfs integer file."""

    path.write_text(f"{value}\n", encoding="utf-8")


def reserve_hugepages(required_mb: int) -> HugepageReservation:
    """Reserve enough free 2 MB hugepages for the requested datapath budget."""

    nr_hugepages_path = HUGEPAGE_SYSFS_DIR / "nr_hugepages"
    free_hugepages_path = HUGEPAGE_SYSFS_DIR / "free_hugepages"
    required_pages = required_mb // HUGEPAGE_SIZE_MB
    original_total_pages = read_int_file(nr_hugepages_path)
    free_pages = read_int_file(free_hugepages_path)

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
        "failed to reserve the required 2 MB hugepages for the privileged controller forwarding smoke test"
    )


def restore_hugepages(reservation: HugepageReservation) -> None:
    """Restore the host hugepage count if this smoke modified it."""

    if not reservation.modified:
        return
    write_int_file(HUGEPAGE_SYSFS_DIR / "nr_hugepages", reservation.original_total_pages)


class ControllerRuntimePrivilegedForwardingSmokeTests(unittest.TestCase):
    """Exercise real controller-managed topology apply plus datapath traffic."""

    @classmethod
    def setUpClass(cls) -> None:
        if os.environ.get("PKTLAB_RUN_PRIVILEGED_CONTROLLER_FORWARDING_SMOKE") != "1":
            raise unittest.SkipTest(
                "set PKTLAB_RUN_PRIVILEGED_CONTROLLER_FORWARDING_SMOKE=1 to run the privileged controller forwarding smoke test"
            )
        if os.geteuid() != 0:
            raise unittest.SkipTest("privileged controller forwarding smoke test requires root")
        if shutil.which("ip") is None:
            raise unittest.SkipTest("privileged controller forwarding smoke test requires the ip command")
        if shutil.which("ping") is None:
            raise unittest.SkipTest("privileged controller forwarding smoke test requires the ping command")

        binary_override = os.environ.get(DEFAULT_DPDKD_BINARY_ENV)
        cls._dpdkd_binary = pathlib.Path(binary_override).resolve() if binary_override else DEFAULT_DPDKD_BINARY
        if not cls._dpdkd_binary.exists():
            raise unittest.SkipTest(
                f"dpdkd binary is missing; build it first at {cls._dpdkd_binary}"
            )

    def setUp(self) -> None:
        token = uuid.uuid4().hex[:8]
        self._src_namespace = f"pktlab-cf-src-{token}"
        self._dpdk_namespace = f"pktlab-cf-dpdk-{token}"
        self._sink_namespace = f"pktlab-cf-sink-{token}"
        self._topology_name = f"controller-forwarding-smoke-{token}"
        self._netns = NetnsRunner()
        self._runtime: ControllerRuntime | None = None
        self._tempdir = tempfile.TemporaryDirectory(prefix="pktlab-ctrld-forwarding-")
        self.addCleanup(self._tempdir.cleanup)

        self._topology_path = pathlib.Path(self._tempdir.name) / "topology.yaml"
        self._socket_path = pathlib.Path(self._tempdir.name) / "dpdkd.sock"
        self._topology_path.write_text(self._topology_yaml(), encoding="utf-8")
        self._validated = validate_topology_config(load_topology_config(self._topology_path))

    def test_apply_and_destroy_forward_real_traffic_through_controller_managed_topology(self) -> None:
        reservation = reserve_hugepages(self._validated.effective_dpdk_config.hugepages_mb)

        try:
            self._runtime = ControllerRuntime(
                ControllerConfig(
                    datapath_binary=str(self._dpdkd_binary),
                    datapath_socket_path=str(self._socket_path),
                    datapath_startup_timeout_seconds=10.0,
                ),
                netns_runner=self._netns,
            )
            self._runtime.start()

            apply_result = self._runtime.apply_topology(str(self._topology_path))

            self.assertTrue(apply_result.applied)
            self.assertEqual(apply_result.topology_name, self._topology_name)
            self.assertEqual(apply_result.datapath_namespace, self._dpdk_namespace)
            self.assertTrue(apply_result.datapath_running)
            self.assertTrue(self._netns.namespace_exists(self._src_namespace))
            self.assertTrue(self._netns.namespace_exists(self._dpdk_namespace))
            self.assertTrue(self._netns.namespace_exists(self._sink_namespace))
            self.assertTrue(self._netns.link_exists(self._dpdk_namespace, "dtap0"))
            self.assertTrue(self._netns.link_exists(self._dpdk_namespace, "dtap1"))
            self.assertEqual(self._bridge_members("br-in"), {"dtap0", "veth-in-k"})
            self.assertEqual(self._bridge_members("br-out"), {"dtap1", "veth-out-k"})

            health = self._runtime.health_snapshot()
            self.assertEqual(health.controller_state, "running")
            self.assertTrue(health.observed_state.topology_applied)
            self.assertIsNotNone(health.datapath_status.health)
            self.assertTrue(health.datapath_status.running)
            self.assertTrue(health.datapath_status.reachable)
            self.assertEqual(health.datapath_status.health.state, "running")
            self.assertTrue(health.datapath_status.health.ports_ready)
            self.assertIn("forwarding loop active", health.datapath_status.health.message)

            for namespace in (self._src_namespace, self._sink_namespace):
                self._netns.set_link_up(namespace=namespace, interface="lo")
            self._netns.replace_address(namespace=self._src_namespace, interface="eth0", cidr="10.0.0.1/24")
            self._netns.replace_address(namespace=self._sink_namespace, interface="eth0", cidr="10.0.0.2/24")

            ping(self._src_namespace, "10.0.0.2")
            ping(self._sink_namespace, "10.0.0.1")

            destroy_result = self._runtime.destroy_topology()
            second_destroy = self._runtime.destroy_topology()

            self.assertFalse(destroy_result.applied)
            self.assertEqual(destroy_result.operation, "destroy")
            self.assertEqual(second_destroy.message, "no topology is currently applied")
            self.assertFalse(self._netns.namespace_exists(self._src_namespace))
            self.assertFalse(self._netns.namespace_exists(self._dpdk_namespace))
            self.assertFalse(self._netns.namespace_exists(self._sink_namespace))
        finally:
            self._cleanup_runtime()
            restore_hugepages(reservation)
            self._cleanup_namespaces()

        print("ok: privileged controller-driven forwarding smoke passed")

    def _cleanup_runtime(self) -> None:
        if self._runtime is None:
            return
        try:
            self._runtime.destroy_topology()
        except Exception:
            pass
        try:
            self._runtime.stop()
        except Exception:
            pass

    def _cleanup_namespaces(self) -> None:
        for namespace in (self._src_namespace, self._dpdk_namespace, self._sink_namespace):
            try:
                self._netns.delete_namespace(namespace)
            except Exception:
                continue

    def _bridge_members(self, bridge: str) -> set[str]:
        result = self._netns.run_ip("-o", "link", "show", "master", bridge, namespace=self._dpdk_namespace)
        members: set[str] = set()
        for line in result.stdout.splitlines():
            _, _, remainder = line.partition(": ")
            interface_token = remainder.split(":", 1)[0]
            members.add(interface_token.split("@", 1)[0])
        return members

    def _topology_yaml(self) -> str:
        return textwrap.dedent(
            f"""
            lab:
              name: {self._topology_name}
            processes:
              dpdkd:
                namespace: {self._dpdk_namespace}
                lcores: "1"
                hugepages_mb: 256
                burst_size: 32
                rx_queue_size: 256
                tx_queue_size: 256
                mempool_size: 4096
            namespaces:
              - name: {self._src_namespace}
              - name: {self._dpdk_namespace}
              - name: {self._sink_namespace}
            links:
              - name: src-to-dpdk
                a: {self._src_namespace}:eth0
                b: {self._dpdk_namespace}:veth-in-k
              - name: dpdk-to-sink
                a: {self._dpdk_namespace}:veth-out-k
                b: {self._sink_namespace}:eth0
            dpdk_ports:
              - name: dtap0
                namespace: {self._dpdk_namespace}
                role: ingress
              - name: dtap1
                namespace: {self._dpdk_namespace}
                role: egress
            routes: []
            rules:
              version: 1
              default_action:
                type: drop
              entries: []
            capture_points:
              - name: src-link
                namespace: {self._src_namespace}
                interface: eth0
            """
        ).strip() + "\n"


if __name__ == "__main__":
    unittest.main()
