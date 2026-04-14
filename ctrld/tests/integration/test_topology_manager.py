"""Integration-style tests for topology orchestration with a fake netns system."""

from __future__ import annotations

import unittest

from pktlab_ctrld.config.topology import parse_topology_config_text
from pktlab_ctrld.config.validation import validate_topology_config
from pktlab_ctrld.error import ErrorCode, PktlabError
from pktlab_ctrld.process.supervisor import DatapathProcessStatus
from pktlab_ctrld.topology.manager import TopologyManager

VALID_TOPOLOGY_YAML = """
lab:
  name: linear-basic
processes:
  dpdkd:
    namespace: dpdk-host
namespaces:
  - name: tg-src
  - name: dpdk-host
  - name: tg-sink
links:
  - name: src-to-host
    a: tg-src:eth0
    b: dpdk-host:veth-in-k
    ip_a: 10.0.0.1/24
    ip_b: 10.0.0.254/24
  - name: host-to-sink
    a: dpdk-host:veth-out-k
    b: tg-sink:eth0
    ip_a: 10.0.1.254/24
    ip_b: 10.0.1.1/24
dpdk_ports:
  - name: dtap0
    namespace: dpdk-host
    role: ingress
  - name: dtap1
    namespace: dpdk-host
    role: egress
routes:
  - namespace: tg-src
    dst: 10.0.1.0/24
    via: 10.0.0.254
  - namespace: tg-sink
    dst: 10.0.0.0/24
    via: 10.0.1.254
rules:
  version: 3
  default_action:
    type: drop
  entries: []
capture_points:
  - name: src-link
    namespace: tg-src
    interface: eth0
"""


class FakeNetnsRunner:
    """In-memory fake of the netns helper API used by topology modules."""

    def __init__(self) -> None:
        self.namespaces: set[str] = set()
        self.links: dict[str, set[str]] = {}
        self.bridges: dict[str, dict[str, set[str]]] = {}
        self.commands: list[tuple[str, ...]] = []

    def list_namespaces(self) -> tuple[str, ...]:
        return tuple(sorted(self.namespaces))

    def namespace_exists(self, namespace: str) -> bool:
        return namespace in self.namespaces

    def ensure_namespace(self, namespace: str) -> None:
        self.commands.append(("netns-add", namespace))
        self.namespaces.add(namespace)
        self.links.setdefault(namespace, set())
        self.bridges.setdefault(namespace, {})

    def delete_namespace(self, namespace: str) -> None:
        self.commands.append(("netns-del", namespace))
        self.namespaces.discard(namespace)
        self.links.pop(namespace, None)
        self.bridges.pop(namespace, None)

    def link_exists(self, namespace: str, interface: str) -> bool:
        return interface in self.links.get(namespace, set()) or interface in self.bridges.get(namespace, {})

    def ensure_veth_pair(
        self,
        *,
        namespace_a: str,
        interface_a: str,
        namespace_b: str,
        interface_b: str,
    ) -> None:
        self.commands.append(("veth-add", namespace_a, interface_a, namespace_b, interface_b))
        self.links.setdefault(namespace_a, set()).add(interface_a)
        self.links.setdefault(namespace_b, set()).add(interface_b)

    def delete_link(self, *, namespace: str, interface: str) -> None:
        self.commands.append(("link-del", namespace, interface))
        self.links.get(namespace, set()).discard(interface)
        self.bridges.get(namespace, {}).pop(interface, None)

    def ensure_bridge(self, *, namespace: str, bridge: str) -> None:
        self.commands.append(("bridge-add", namespace, bridge))
        self.bridges.setdefault(namespace, {}).setdefault(bridge, set())

    def replace_address(self, *, namespace: str, interface: str, cidr: str) -> None:
        self.commands.append(("addr-replace", namespace, interface, cidr))

    def replace_route(self, *, namespace: str, dst: str, via: str) -> None:
        self.commands.append(("route-replace", namespace, dst, via))

    def attach_to_bridge(self, *, namespace: str, interface: str, bridge: str) -> None:
        self.commands.append(("bridge-attach", namespace, interface, bridge))
        self.bridges.setdefault(namespace, {}).setdefault(bridge, set()).add(interface)

    def set_link_up(self, *, namespace: str, interface: str) -> None:
        self.commands.append(("link-up", namespace, interface))


class TopologyManagerIntegrationTests(unittest.TestCase):
    """Verify the topology manager order and reverse-safe cleanup."""

    def setUp(self) -> None:
        topology = parse_topology_config_text(VALID_TOPOLOGY_YAML, source="integration-topology")
        self.validated = validate_topology_config(topology)
        self.netns = FakeNetnsRunner()
        self.lifecycle: list[tuple[str, ...]] = []

        def start_datapath(validated_topology):
            self.lifecycle.append(("start-datapath", validated_topology.requested_dpdk_config.namespace))
            self.netns.links.setdefault(validated_topology.requested_dpdk_config.namespace, set()).update(
                {"dtap0", "dtap1"}
            )
            return DatapathProcessStatus(
                managed=True,
                socket_path="/tmp/pktlab.sock",
                pid=1234,
                running=True,
                reachable=True,
            )

        def stop_datapath() -> None:
            self.lifecycle.append(("stop-datapath",))

        self.manager = TopologyManager(
            netns=self.netns,
            load_topology=lambda _: topology,
            validate_topology=lambda _: self.validated,
            start_datapath=start_datapath,
            stop_datapath=stop_datapath,
        )

    def test_apply_creates_namespaces_links_routes_and_bridge_membership(self) -> None:
        result = self.manager.apply("lab/topology.yaml")

        self.assertTrue(result.applied)
        self.assertEqual(result.topology_name, "linear-basic")
        self.assertEqual(self.lifecycle, [("start-datapath", "dpdk-host")])
        self.assertEqual(self.netns.list_namespaces(), ("dpdk-host", "tg-sink", "tg-src"))
        self.assertEqual(self.netns.bridges["dpdk-host"]["br-in"], {"dtap0", "veth-in-k"})
        self.assertEqual(self.netns.bridges["dpdk-host"]["br-out"], {"dtap1", "veth-out-k"})
        self.assertIn(("route-replace", "tg-src", "10.0.1.0/24", "10.0.0.254"), self.netns.commands)
        self.assertIn(("link-up", "dpdk-host", "dtap0"), self.netns.commands)
        self.assertIn(("link-up", "dpdk-host", "br-out"), self.netns.commands)
        self.assertLess(
            self.netns.commands.index(("link-up", "tg-src", "eth0")),
            self.netns.commands.index(("route-replace", "tg-src", "10.0.1.0/24", "10.0.0.254")),
        )
        self.assertLess(
            self.netns.commands.index(("link-up", "tg-sink", "eth0")),
            self.netns.commands.index(("route-replace", "tg-sink", "10.0.0.0/24", "10.0.1.254")),
        )

    def test_destroy_runs_reverse_safe_cleanup_and_is_idempotent(self) -> None:
        self.manager.apply("lab/topology.yaml")

        destroy_result = self.manager.destroy()
        second_destroy = self.manager.destroy()

        self.assertFalse(destroy_result.applied)
        self.assertEqual(destroy_result.operation, "destroy")
        self.assertEqual(second_destroy.message, "no topology is currently applied")
        self.assertIn(("stop-datapath",), self.lifecycle)
        self.assertIn(("link-del", "dpdk-host", "br-out"), self.netns.commands)
        self.assertIn(("netns-del", "tg-src"), self.netns.commands)

    def test_reapply_same_config_path_reconciles_again_instead_of_nooping(self) -> None:
        first_apply = self.manager.apply("lab/topology.yaml")
        second_apply = self.manager.apply("lab/topology.yaml")

        self.assertTrue(first_apply.applied)
        self.assertTrue(second_apply.applied)
        self.assertEqual(second_apply.message, "topology applied")
        self.assertEqual(
            self.lifecycle,
            [
                ("start-datapath", "dpdk-host"),
                ("stop-datapath",),
                ("start-datapath", "dpdk-host"),
            ],
        )

    def test_failed_apply_surfaces_cleanup_errors(self) -> None:
        def start_datapath(_validated_topology):
            raise PktlabError(
                ErrorCode.PROCESS_ERROR,
                "datapath launch failed",
            )

        def stop_datapath() -> None:
            raise PktlabError(
                ErrorCode.PROCESS_ERROR,
                "datapath stop failed",
            )

        topology = parse_topology_config_text(VALID_TOPOLOGY_YAML, source="integration-topology")
        manager = TopologyManager(
            netns=FakeNetnsRunner(),
            load_topology=lambda _: topology,
            validate_topology=lambda _: self.validated,
            start_datapath=start_datapath,
            stop_datapath=stop_datapath,
        )

        with self.assertRaises(PktlabError) as ctx:
            manager.apply("lab/topology.yaml")

        self.assertEqual(ctx.exception.code, ErrorCode.PROCESS_ERROR)
        self.assertEqual(ctx.exception.message, "datapath launch failed")
        self.assertIn("cleanup_error", ctx.exception.context)
        self.assertEqual(
            ctx.exception.context["cleanup_error"]["code"],
            ErrorCode.TOPOLOGY_DESTROY_ERROR.value,
        )


if __name__ == "__main__":
    unittest.main()
