"""Unit tests for topology parsing, validation, and runtime policy derivation."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from pktlab_ctrld.config.topology import load_topology_config, parse_topology_config_text
from pktlab_ctrld.config.validation import (
    derive_effective_dpdk_runtime,
    validate_topology_config,
)
from pktlab_ctrld.error import ConfigParseError, ValidationError
from pktlab_ctrld.types import DpdkProcessConfigModel

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
  entries:
    - id: 10
      priority: 10
      match:
        proto: udp
        dst_port: 53
      action:
        type: forward
        port: dtap1
capture_points:
  - name: src-link
    namespace: tg-src
    interface: eth0
  - name: dpdk-in
    namespace: dpdk-host
    interface: dtap0
"""

INVALID_TOPOLOGY_YAML = """
lab:
  name: broken-lab
processes:
  dpdkd:
    namespace: missing-host
    hugepages_mb: 128
namespaces:
  - name: tg-src
  - name: tg-src
links:
  - name: dup-link
    a: tg-src:eth0
    b: missing-host:veth0
    ip_a: 10.0.0.1/24
    ip_b: 10.0.1.1/24
dpdk_ports:
  - name: dtap0
    namespace: tg-src
    role: ingress
  - name: dtap0
    namespace: tg-src
    role: ingress
routes:
  - namespace: tg-sink
    dst: 10.0.1.0/24
    via: 10.0.9.1
rules:
  version: 1
  default_action:
    type: forward
    port: dtap9
  entries:
    - id: 5
      priority: 1
      match:
        proto: udp
      action:
        type: mirror
        port: dtap9
capture_points:
  - name: cp1
    namespace: tg-src
    interface: dtap9
"""


class TopologyConfigTests(unittest.TestCase):
    """Keep topology parsing and validation explicit and deterministic."""

    def test_parse_and_validate_topology_with_conservative_defaults(self) -> None:
        topology = parse_topology_config_text(VALID_TOPOLOGY_YAML, source="inline-topology")

        validated = validate_topology_config(topology)

        self.assertEqual(validated.topology.lab.name, "linear-basic")
        self.assertEqual(validated.requested_dpdk_config.namespace, "dpdk-host")
        self.assertEqual(validated.effective_dpdk_config.lcores, "1")
        self.assertEqual(validated.effective_dpdk_config.lcore_count, 1)
        self.assertEqual(validated.effective_dpdk_config.burst_size, 32)
        self.assertEqual(validated.effective_dpdk_config.rx_queue_size, 256)
        self.assertEqual(validated.effective_dpdk_config.tx_queue_size, 256)
        self.assertEqual(validated.effective_dpdk_config.mempool_size, 4096)
        self.assertEqual(validated.effective_dpdk_config.hugepages_mb, 256)
        self.assertEqual(validated.namespace_interfaces["dpdk-host"], ("dtap0", "dtap1", "veth-in-k", "veth-out-k"))

    def test_load_topology_config_from_disk(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pktlab-topology-") as tmpdir:
            config_path = pathlib.Path(tmpdir) / "topology.yaml"
            config_path.write_text(VALID_TOPOLOGY_YAML, encoding="utf-8")

            topology = load_topology_config(config_path)

        self.assertEqual(topology.lab.name, "linear-basic")

    def test_parser_reports_yaml_and_shape_errors(self) -> None:
        with self.assertRaises(ConfigParseError) as yaml_context:
            parse_topology_config_text("lab: [", source="broken-yaml")
        self.assertEqual(yaml_context.exception.code.value, "CONFIG_PARSE_ERROR")

        with self.assertRaises(ConfigParseError) as root_context:
            parse_topology_config_text("- not-a-mapping", source="broken-root")
        self.assertEqual(root_context.exception.context["root_type"], "list")

    def test_validation_reports_structured_cross_reference_errors(self) -> None:
        topology = parse_topology_config_text(INVALID_TOPOLOGY_YAML, source="invalid-topology")

        with self.assertRaises(ValidationError) as context:
            validate_topology_config(topology)

        self.assertEqual(context.exception.code.value, "TOPOLOGY_VALIDATION_ERROR")
        issues = list(context.exception.issues)
        issue_codes = {issue["code"] for issue in issues}
        issue_paths = {issue["path"] for issue in issues}
        self.assertIn("duplicate_name", issue_codes)
        self.assertIn("unknown_namespace", issue_codes)
        self.assertIn("invalid_port_roles", issue_codes)
        self.assertIn("undersized_hugepages", issue_codes)
        self.assertIn("processes.dpdkd.namespace", issue_paths)
        self.assertIn("routes[0].namespace", issue_paths)

    def test_effective_runtime_derivation_rejects_undersized_memory(self) -> None:
        requested = DpdkProcessConfigModel(
            namespace="dpdk-host",
            lcores="1-2",
            hugepages_mb=128,
            rx_queue_size=512,
            tx_queue_size=512,
            burst_size=64,
            mempool_size=8192,
        )

        with self.assertRaises(ValidationError) as context:
            derive_effective_dpdk_runtime(requested, port_count=2)

        self.assertEqual(context.exception.code.value, "TOPOLOGY_VALIDATION_ERROR")
        self.assertTrue(
            any(issue["code"] == "undersized_hugepages" for issue in context.exception.issues)
        )


if __name__ == "__main__":
    unittest.main()
