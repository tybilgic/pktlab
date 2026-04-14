"""Opt-in privileged smoke test for real topology apply/destroy host mutations."""

from __future__ import annotations

import os
import shutil
import tempfile
import textwrap
import unittest
import uuid
from pathlib import Path

from pktlab_ctrld.process.supervisor import DatapathProcessStatus
from pktlab_ctrld.topology.manager import TopologyManager
from pktlab_ctrld.util.netns import NetnsRunner


class TopologyManagerPrivilegedSmokeTests(unittest.TestCase):
    """Exercise real host-backed topology apply/destroy with synthetic datapath links."""

    @classmethod
    def setUpClass(cls) -> None:
        if os.environ.get("PKTLAB_RUN_PRIVILEGED_TOPOLOGY_SMOKE") != "1":
            raise unittest.SkipTest(
                "set PKTLAB_RUN_PRIVILEGED_TOPOLOGY_SMOKE=1 to run the privileged topology smoke test"
            )
        if os.geteuid() != 0:
            raise unittest.SkipTest("privileged topology smoke test requires root or CAP_NET_ADMIN")
        if shutil.which("ip") is None:
            raise unittest.SkipTest("privileged topology smoke test requires the ip command")

    def setUp(self) -> None:
        token = uuid.uuid4().hex[:8]
        self._src_namespace = f"pktlab-smoke-src-{token}"
        self._dpdk_namespace = f"pktlab-smoke-dpdk-{token}"
        self._sink_namespace = f"pktlab-smoke-sink-{token}"
        self._topology_name = f"privileged-smoke-{token}"
        self._netns = NetnsRunner()
        self._lifecycle: list[tuple[str, ...]] = []
        self._tempdir = tempfile.TemporaryDirectory(prefix="pktlab-topology-smoke-")
        self.addCleanup(self._tempdir.cleanup)
        self.addCleanup(self._cleanup_namespaces)
        self._topology_path = Path(self._tempdir.name) / "topology.yaml"
        self._topology_path.write_text(self._topology_yaml(), encoding="utf-8")
        self._manager = TopologyManager(
            netns=self._netns,
            start_datapath=self._start_datapath,
            stop_datapath=self._stop_datapath,
        )

    def test_apply_and_destroy_mutate_the_real_host_network_stack(self) -> None:
        apply_result = self._manager.apply(str(self._topology_path))

        self.assertTrue(apply_result.applied)
        self.assertEqual(apply_result.topology_name, self._topology_name)
        self.assertEqual(self._lifecycle, [("start-datapath", self._dpdk_namespace)])
        self.assertTrue(self._netns.namespace_exists(self._src_namespace))
        self.assertTrue(self._netns.namespace_exists(self._dpdk_namespace))
        self.assertTrue(self._netns.namespace_exists(self._sink_namespace))
        self.assertTrue(self._netns.link_exists(self._dpdk_namespace, "dtap0"))
        self.assertTrue(self._netns.link_exists(self._dpdk_namespace, "dtap1"))
        self.assertTrue(self._netns.link_exists(self._dpdk_namespace, "br-in"))
        self.assertTrue(self._netns.link_exists(self._dpdk_namespace, "br-out"))
        self.assertEqual(self._bridge_members(self._dpdk_namespace, "br-in"), {"dtap0", "veth-in-k"})
        self.assertEqual(self._bridge_members(self._dpdk_namespace, "br-out"), {"dtap1", "veth-out-k"})
        self.assert_route(self._src_namespace, "10.0.1.0/24", "10.0.0.254")
        self.assert_route(self._sink_namespace, "10.0.0.0/24", "10.0.1.254")

        destroy_result = self._manager.destroy()
        second_destroy = self._manager.destroy()

        self.assertFalse(destroy_result.applied)
        self.assertEqual(destroy_result.operation, "destroy")
        self.assertEqual(second_destroy.message, "no topology is currently applied")
        self.assertEqual(
            self._lifecycle,
            [("start-datapath", self._dpdk_namespace), ("stop-datapath",)],
        )
        self.assertFalse(self._netns.namespace_exists(self._src_namespace))
        self.assertFalse(self._netns.namespace_exists(self._dpdk_namespace))
        self.assertFalse(self._netns.namespace_exists(self._sink_namespace))

    def _start_datapath(self, validated_topology) -> DatapathProcessStatus:
        namespace = validated_topology.requested_dpdk_config.namespace
        self._lifecycle.append(("start-datapath", namespace))
        for interface in ("dtap0", "dtap1"):
            if not self._netns.link_exists(namespace, interface):
                self._netns.run_ip("link", "add", "name", interface, "type", "dummy", namespace=namespace)
        return DatapathProcessStatus(
            managed=True,
            socket_path="/tmp/pktlab-privileged-topology-smoke.sock",
            pid=os.getpid(),
            running=True,
            reachable=True,
        )

    def _stop_datapath(self) -> None:
        self._lifecycle.append(("stop-datapath",))

    def _cleanup_namespaces(self) -> None:
        for namespace in (self._src_namespace, self._dpdk_namespace, self._sink_namespace):
            try:
                self._netns.delete_namespace(namespace)
            except Exception:
                continue

    def _topology_yaml(self) -> str:
        return textwrap.dedent(
            f"""
            lab:
              name: {self._topology_name}
            processes:
              dpdkd:
                namespace: {self._dpdk_namespace}
            namespaces:
              - name: {self._src_namespace}
              - name: {self._dpdk_namespace}
              - name: {self._sink_namespace}
            links:
              - name: src-to-host
                a: {self._src_namespace}:eth0
                b: {self._dpdk_namespace}:veth-in-k
                ip_a: 10.0.0.1/24
                ip_b: 10.0.0.254/24
              - name: host-to-sink
                a: {self._dpdk_namespace}:veth-out-k
                b: {self._sink_namespace}:eth0
                ip_a: 10.0.1.254/24
                ip_b: 10.0.1.1/24
            dpdk_ports:
              - name: dtap0
                namespace: {self._dpdk_namespace}
                role: ingress
              - name: dtap1
                namespace: {self._dpdk_namespace}
                role: egress
            routes:
              - namespace: {self._src_namespace}
                dst: 10.0.1.0/24
                via: 10.0.0.254
              - namespace: {self._sink_namespace}
                dst: 10.0.0.0/24
                via: 10.0.1.254
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

    def _bridge_members(self, namespace: str, bridge: str) -> set[str]:
        result = self._netns.run_ip("-o", "link", "show", "master", bridge, namespace=namespace)
        members: set[str] = set()
        for line in result.stdout.splitlines():
            _, _, remainder = line.partition(": ")
            interface_token = remainder.split(":", 1)[0]
            members.add(interface_token.split("@", 1)[0])
        return members

    def assert_route(self, namespace: str, dst: str, via: str) -> None:
        result = self._netns.run_ip("route", "show", dst, namespace=namespace)
        self.assertIn(f"{dst} via {via}", result.stdout)


if __name__ == "__main__":
    unittest.main()
