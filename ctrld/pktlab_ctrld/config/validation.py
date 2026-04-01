"""Topology and rules validation plus effective runtime policy derivation."""

from __future__ import annotations

import ipaddress
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Collection, Mapping

from pktlab_ctrld.error import ErrorCode, ValidationError
from pktlab_ctrld.types import (
    DpdkProcessConfigModel,
    EffectiveDpdkRuntimeModel,
    RulesetModel,
    TopologyConfigModel,
)

DEFAULT_LCORES = "1"
DEFAULT_BURST_SIZE = 32
DEFAULT_RX_QUEUE_SIZE = 256
DEFAULT_TX_QUEUE_SIZE = 256
DEFAULT_HUGEPAGE_SIZE_MB = 2
DEFAULT_HUGEPAGES_FLOOR_MB = 256
MAX_LCORE_COUNT = 8
MAX_BURST_SIZE = 256
MAX_QUEUE_SIZE = 4096
MAX_MEMPOOL_SIZE = 65536
MAX_HUGEPAGES_MB = 1024
MIN_MEMPOOL_SIZE = 2048
MEMPOOL_HEADROOM_FACTOR = 4
MBUF_MEMORY_ESTIMATE_BYTES = 4096
FIXED_RUNTIME_OVERHEAD_MB = 64
INGRESS_BRIDGE_KERNEL_INTERFACE = "veth-in-k"
EGRESS_BRIDGE_KERNEL_INTERFACE = "veth-out-k"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Single structured validation issue."""

    path: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Return a serializable issue payload."""

        return {
            "path": self.path,
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidatedRuleset:
    """Semantically validated standalone ruleset."""

    ruleset: RulesetModel
    allowed_port_names: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class ValidatedTopologyConfig:
    """Validated topology config plus the resolved datapath runtime profile."""

    topology: TopologyConfigModel
    requested_dpdk_config: DpdkProcessConfigModel
    effective_dpdk_config: EffectiveDpdkRuntimeModel
    namespace_names: frozenset[str] = field(default_factory=frozenset)
    dpdk_port_names: frozenset[str] = field(default_factory=frozenset)
    namespace_interfaces: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "namespace_names", frozenset(self.namespace_names))
        object.__setattr__(self, "dpdk_port_names", frozenset(self.dpdk_port_names))
        normalized_interfaces = {
            namespace: tuple(sorted(set(interfaces)))
            for namespace, interfaces in dict(self.namespace_interfaces).items()
        }
        object.__setattr__(
            self,
            "namespace_interfaces",
            MappingProxyType(normalized_interfaces),
        )


def validate_topology_config(config: TopologyConfigModel) -> ValidatedTopologyConfig:
    """Validate a parsed topology config and derive the effective datapath runtime."""

    issues: list[ValidationIssue] = []
    namespace_names = _collect_duplicate_names(config.namespaces, "namespaces", issues)
    interface_names_by_namespace: dict[str, set[str]] = {
        namespace_name: set() for namespace_name in namespace_names
    }
    connected_networks_by_namespace: dict[str, list[ipaddress.IPv4Network]] = defaultdict(list)

    dpdk_namespace = config.processes.dpdkd.namespace
    if dpdk_namespace not in namespace_names:
        issues.append(
            ValidationIssue(
                path="processes.dpdkd.namespace",
                code="unknown_namespace",
                message=f"dpdkd namespace '{dpdk_namespace}' is not declared in namespaces",
            )
        )

    _collect_link_issues(
        config,
        namespace_names=namespace_names,
        interface_names_by_namespace=interface_names_by_namespace,
        connected_networks_by_namespace=connected_networks_by_namespace,
        issues=issues,
    )
    dpdk_port_names = _collect_dpdk_port_issues(
        config,
        namespace_names=namespace_names,
        dpdk_namespace=dpdk_namespace,
        interface_names_by_namespace=interface_names_by_namespace,
        issues=issues,
    )
    _collect_route_issues(
        config,
        namespace_names=namespace_names,
        connected_networks_by_namespace=connected_networks_by_namespace,
        issues=issues,
    )
    _collect_capture_point_issues(
        config,
        namespace_names=namespace_names,
        interface_names_by_namespace=interface_names_by_namespace,
        issues=issues,
    )
    _collect_bridge_side_interface_issues(
        dpdk_namespace=dpdk_namespace,
        interface_names_by_namespace=interface_names_by_namespace,
        issues=issues,
    )
    _collect_ruleset_issues(
        config.rules,
        path_prefix="rules",
        allowed_port_names=dpdk_port_names,
        issues=issues,
    )

    effective_dpdk_config = _derive_effective_dpdk_runtime(
        config.processes.dpdkd,
        port_count=len(config.dpdk_ports),
        issues=issues,
        path_prefix="processes.dpdkd",
    )
    if issues:
        raise ValidationError(
            "topology config failed semantic validation",
            code=ErrorCode.TOPOLOGY_VALIDATION_ERROR,
            issues=[issue.to_dict() for issue in issues],
        )

    return ValidatedTopologyConfig(
        topology=config,
        requested_dpdk_config=config.processes.dpdkd,
        effective_dpdk_config=effective_dpdk_config,
        namespace_names=frozenset(namespace_names),
        dpdk_port_names=frozenset(dpdk_port_names),
        namespace_interfaces={
            namespace: tuple(sorted(interfaces))
            for namespace, interfaces in interface_names_by_namespace.items()
        },
    )


def validate_ruleset(
    ruleset: RulesetModel,
    *,
    allowed_port_names: Collection[str] | None = None,
) -> ValidatedRuleset:
    """Validate a standalone ruleset against optional known datapath port names."""

    issues: list[ValidationIssue] = []
    _collect_ruleset_issues(
        ruleset,
        allowed_port_names=allowed_port_names,
        issues=issues,
    )
    if issues:
        raise ValidationError(
            "rules config failed semantic validation",
            code=ErrorCode.RULE_VALIDATION_ERROR,
            issues=[issue.to_dict() for issue in issues],
        )

    return ValidatedRuleset(
        ruleset=ruleset,
        allowed_port_names=frozenset(allowed_port_names or ()),
    )


def derive_effective_dpdk_runtime(
    requested: DpdkProcessConfigModel,
    *,
    port_count: int,
) -> EffectiveDpdkRuntimeModel:
    """Resolve controller defaults for datapath launch parameters."""

    issues: list[ValidationIssue] = []
    effective = _derive_effective_dpdk_runtime(
        requested,
        port_count=port_count,
        issues=issues,
        path_prefix="processes.dpdkd",
    )
    if issues:
        raise ValidationError(
            "effective datapath runtime config is invalid",
            code=ErrorCode.TOPOLOGY_VALIDATION_ERROR,
            issues=[issue.to_dict() for issue in issues],
        )
    return effective


def _derive_effective_dpdk_runtime(
    requested: DpdkProcessConfigModel,
    *,
    port_count: int,
    issues: list[ValidationIssue],
    path_prefix: str,
) -> EffectiveDpdkRuntimeModel:
    lcores = requested.lcores or DEFAULT_LCORES
    lcore_ids = _parse_lcore_spec(lcores, path=f"{path_prefix}.lcores", issues=issues)
    lcore_count = len(lcore_ids) if lcore_ids else 1
    if lcore_count > MAX_LCORE_COUNT:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.lcores",
                code="oversized_lcore_set",
                message=f"lcore set resolves to {lcore_count} lcores; the controller caps this at {MAX_LCORE_COUNT} for the MVP",
            )
        )

    rx_queue_size = requested.rx_queue_size or DEFAULT_RX_QUEUE_SIZE
    tx_queue_size = requested.tx_queue_size or DEFAULT_TX_QUEUE_SIZE
    burst_size = requested.burst_size or DEFAULT_BURST_SIZE

    if rx_queue_size > MAX_QUEUE_SIZE:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.rx_queue_size",
                code="oversized_queue",
                message=f"rx_queue_size {rx_queue_size} exceeds the controller limit of {MAX_QUEUE_SIZE}",
            )
        )
    if tx_queue_size > MAX_QUEUE_SIZE:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.tx_queue_size",
                code="oversized_queue",
                message=f"tx_queue_size {tx_queue_size} exceeds the controller limit of {MAX_QUEUE_SIZE}",
            )
        )
    if burst_size > MAX_BURST_SIZE:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.burst_size",
                code="oversized_burst",
                message=f"burst_size {burst_size} exceeds the controller limit of {MAX_BURST_SIZE}",
            )
        )
    if burst_size > min(rx_queue_size, tx_queue_size):
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.burst_size",
                code="burst_exceeds_queue",
                message="burst_size must not exceed either queue size",
            )
        )

    recommended_mempool_size = _round_up_power_of_two(
        max(
            MIN_MEMPOOL_SIZE,
            port_count * (rx_queue_size + tx_queue_size) * MEMPOOL_HEADROOM_FACTOR,
        )
    )
    mempool_size = requested.mempool_size or recommended_mempool_size
    if mempool_size < recommended_mempool_size:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.mempool_size",
                code="undersized_mempool",
                message=(
                    f"mempool_size {mempool_size} is too small for {port_count} ports and the configured queues; "
                    f"minimum recommended value is {recommended_mempool_size}"
                ),
            )
        )
    if mempool_size > MAX_MEMPOOL_SIZE:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.mempool_size",
                code="oversized_mempool",
                message=f"mempool_size {mempool_size} exceeds the controller limit of {MAX_MEMPOOL_SIZE}",
            )
        )

    recommended_hugepages_mb = _recommended_hugepages_mb(mempool_size)
    hugepages_mb = requested.hugepages_mb or recommended_hugepages_mb
    if hugepages_mb % DEFAULT_HUGEPAGE_SIZE_MB != 0:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.hugepages_mb",
                code="invalid_hugepage_multiple",
                message=f"hugepages_mb must be a multiple of {DEFAULT_HUGEPAGE_SIZE_MB} MB",
            )
        )
    if hugepages_mb < recommended_hugepages_mb:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.hugepages_mb",
                code="undersized_hugepages",
                message=(
                    f"hugepages_mb {hugepages_mb} is below the controller floor of {recommended_hugepages_mb} MB "
                    "for the current mempool and safety margin"
                ),
            )
        )
    if hugepages_mb > MAX_HUGEPAGES_MB:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.hugepages_mb",
                code="oversized_hugepages",
                message=f"hugepages_mb {hugepages_mb} exceeds the controller limit of {MAX_HUGEPAGES_MB} MB",
            )
        )

    return EffectiveDpdkRuntimeModel(
        lcores=lcores,
        lcore_count=lcore_count,
        hugepage_size_mb=DEFAULT_HUGEPAGE_SIZE_MB,
        hugepages_mb=hugepages_mb,
        burst_size=burst_size,
        rx_queue_size=rx_queue_size,
        tx_queue_size=tx_queue_size,
        mempool_size=mempool_size,
        port_count=port_count,
    )


def _collect_duplicate_names(
    items: Collection[object],
    path_prefix: str,
    issues: list[ValidationIssue],
) -> set[str]:
    seen: dict[str, int] = {}
    names: set[str] = set()
    for index, item in enumerate(items):
        name = getattr(item, "name")
        names.add(name)
        first_index = seen.setdefault(name, index)
        if first_index != index:
            issues.append(
                ValidationIssue(
                    path=f"{path_prefix}[{index}].name",
                    code="duplicate_name",
                    message=f"{path_prefix} name '{name}' duplicates the entry at index {first_index}",
                )
            )
    return names


def _collect_link_issues(
    config: TopologyConfigModel,
    *,
    namespace_names: set[str],
    interface_names_by_namespace: dict[str, set[str]],
    connected_networks_by_namespace: dict[str, list[ipaddress.IPv4Network]],
    issues: list[ValidationIssue],
) -> None:
    _collect_duplicate_names(config.links, "links", issues)
    seen_interfaces: dict[tuple[str, str], int] = {}

    for index, link in enumerate(config.links):
        a_ref = _parse_interface_ref(link.a, path=f"links[{index}].a", issues=issues)
        b_ref = _parse_interface_ref(link.b, path=f"links[{index}].b", issues=issues)
        if a_ref is not None and b_ref is not None and a_ref == b_ref:
            issues.append(
                ValidationIssue(
                    path=f"links[{index}]",
                    code="self_link",
                    message="link endpoints must refer to two different interfaces",
                )
            )

        for path, ref in (
            (f"links[{index}].a", a_ref),
            (f"links[{index}].b", b_ref),
        ):
            if ref is None:
                continue
            namespace_name, interface_name = ref
            if namespace_name not in namespace_names:
                issues.append(
                    ValidationIssue(
                        path=path,
                        code="unknown_namespace",
                        message=f"namespace '{namespace_name}' is not declared in namespaces",
                    )
                )
                continue

            previous_index = seen_interfaces.setdefault(ref, index)
            if previous_index != index:
                issues.append(
                    ValidationIssue(
                        path=path,
                        code="interface_reused",
                        message=f"interface '{namespace_name}:{interface_name}' is already used by links[{previous_index}]",
                    )
                )
            interface_names_by_namespace[namespace_name].add(interface_name)

        if (link.ip_a is None) != (link.ip_b is None):
            issues.append(
                ValidationIssue(
                    path=f"links[{index}]",
                    code="incomplete_link_addressing",
                    message="ip_a and ip_b must either both be provided or both be omitted",
                )
            )
            continue

        if link.ip_a is None or link.ip_b is None:
            continue

        ip_a = _parse_interface_address(
            link.ip_a,
            path=f"links[{index}].ip_a",
            issues=issues,
        )
        ip_b = _parse_interface_address(
            link.ip_b,
            path=f"links[{index}].ip_b",
            issues=issues,
        )
        if ip_a is None or ip_b is None:
            continue
        if ip_a.network != ip_b.network:
            issues.append(
                ValidationIssue(
                    path=f"links[{index}]",
                    code="mismatched_subnets",
                    message="link endpoint addresses must belong to the same IPv4 network",
                )
            )
            continue
        if a_ref is not None and a_ref[0] in namespace_names:
            connected_networks_by_namespace[a_ref[0]].append(ip_a.network)
        if b_ref is not None and b_ref[0] in namespace_names:
            connected_networks_by_namespace[b_ref[0]].append(ip_b.network)


def _collect_dpdk_port_issues(
    config: TopologyConfigModel,
    *,
    namespace_names: set[str],
    dpdk_namespace: str,
    interface_names_by_namespace: dict[str, set[str]],
    issues: list[ValidationIssue],
) -> set[str]:
    port_names = _collect_duplicate_names(config.dpdk_ports, "dpdk_ports", issues)
    roles = Counter(port.role for port in config.dpdk_ports)

    for role in ("ingress", "egress"):
        if roles[role] != 1:
            issues.append(
                ValidationIssue(
                    path="dpdk_ports",
                    code="invalid_port_roles",
                    message="dpdk_ports must declare exactly one ingress port and one egress port for the MVP",
                )
            )
            break

    for index, port in enumerate(config.dpdk_ports):
        if port.namespace not in namespace_names:
            issues.append(
                ValidationIssue(
                    path=f"dpdk_ports[{index}].namespace",
                    code="unknown_namespace",
                    message=f"namespace '{port.namespace}' is not declared in namespaces",
                )
            )
            continue
        if port.namespace != dpdk_namespace:
            issues.append(
                ValidationIssue(
                    path=f"dpdk_ports[{index}].namespace",
                    code="port_namespace_mismatch",
                    message=(
                        f"dpdk port '{port.name}' must live in the datapath namespace '{dpdk_namespace}', "
                        f"not '{port.namespace}'"
                    ),
                )
            )
        if port.name in interface_names_by_namespace[port.namespace]:
            issues.append(
                ValidationIssue(
                    path=f"dpdk_ports[{index}].name",
                    code="interface_name_conflict",
                    message=f"interface name '{port.name}' is already used in namespace '{port.namespace}'",
                )
            )
            continue
        interface_names_by_namespace[port.namespace].add(port.name)

    return port_names


def _collect_route_issues(
    config: TopologyConfigModel,
    *,
    namespace_names: set[str],
    connected_networks_by_namespace: Mapping[str, list[ipaddress.IPv4Network]],
    issues: list[ValidationIssue],
) -> None:
    for index, route in enumerate(config.routes):
        namespace_path = f"routes[{index}].namespace"
        if route.namespace not in namespace_names:
            issues.append(
                ValidationIssue(
                    path=namespace_path,
                    code="unknown_namespace",
                    message=f"namespace '{route.namespace}' is not declared in namespaces",
                )
            )
            continue

        _parse_network(route.dst, path=f"routes[{index}].dst", issues=issues)
        via = _parse_address(route.via, path=f"routes[{index}].via", issues=issues)
        if via is None:
            continue

        connected_networks = connected_networks_by_namespace.get(route.namespace, ())
        if not connected_networks:
            issues.append(
                ValidationIssue(
                    path=f"routes[{index}]",
                    code="unreachable_gateway",
                    message=f"namespace '{route.namespace}' has no directly addressed links that can reach route via {route.via}",
                )
            )
            continue

        if not any(via in network for network in connected_networks):
            issues.append(
                ValidationIssue(
                    path=f"routes[{index}].via",
                    code="unreachable_gateway",
                    message=f"gateway '{route.via}' is not reachable from any addressed link in namespace '{route.namespace}'",
                )
            )


def _collect_capture_point_issues(
    config: TopologyConfigModel,
    *,
    namespace_names: set[str],
    interface_names_by_namespace: Mapping[str, set[str]],
    issues: list[ValidationIssue],
) -> None:
    _collect_duplicate_names(config.capture_points, "capture_points", issues)
    for index, capture_point in enumerate(config.capture_points):
        if capture_point.namespace not in namespace_names:
            issues.append(
                ValidationIssue(
                    path=f"capture_points[{index}].namespace",
                    code="unknown_namespace",
                    message=f"namespace '{capture_point.namespace}' is not declared in namespaces",
                )
            )
            continue

        known_interfaces = interface_names_by_namespace.get(capture_point.namespace, set())
        if capture_point.interface not in known_interfaces:
            issues.append(
                ValidationIssue(
                    path=f"capture_points[{index}].interface",
                    code="unknown_interface",
                    message=(
                        f"interface '{capture_point.interface}' is not declared in namespace '{capture_point.namespace}' "
                        "through links or dpdk_ports"
                    ),
                )
                )


def _collect_bridge_side_interface_issues(
    *,
    dpdk_namespace: str,
    interface_names_by_namespace: Mapping[str, set[str]],
    issues: list[ValidationIssue],
) -> None:
    bridge_side_interfaces = interface_names_by_namespace.get(dpdk_namespace, set())
    for interface_name in (INGRESS_BRIDGE_KERNEL_INTERFACE, EGRESS_BRIDGE_KERNEL_INTERFACE):
        if interface_name not in bridge_side_interfaces:
            issues.append(
                ValidationIssue(
                    path="links",
                    code="missing_bridge_side_interface",
                    message=(
                        f"dpdk namespace '{dpdk_namespace}' must define bridge-side interface "
                        f"'{interface_name}' through the topology links"
                    ),
                )
            )


def _collect_ruleset_issues(
    ruleset: RulesetModel,
    *,
    path_prefix: str | None = None,
    allowed_port_names: Collection[str] | None,
    issues: list[ValidationIssue],
) -> None:
    allowed_ports = set(allowed_port_names or ())
    seen_ids: dict[int, int] = {}
    _validate_rule_action(
        ruleset.default_action,
        path=_path_with_prefix(path_prefix, "default_action"),
        allowed_port_names=allowed_ports if allowed_port_names is not None else None,
        issues=issues,
    )

    for index, rule in enumerate(ruleset.entries):
        entry_path = _path_with_prefix(path_prefix, f"entries[{index}]")
        first_index = seen_ids.setdefault(rule.id, index)
        if first_index != index:
            issues.append(
                ValidationIssue(
                    path=f"{entry_path}.id",
                    code="duplicate_rule_id",
                    message=f"rule id {rule.id} duplicates the entry at index {first_index}",
                )
            )

        _validate_rule_match(rule, path_prefix=entry_path, issues=issues)
        _validate_rule_action(
            rule.action,
            path=f"{entry_path}.action",
            allowed_port_names=allowed_ports if allowed_port_names is not None else None,
            issues=issues,
        )


def _path_with_prefix(path_prefix: str | None, suffix: str) -> str:
    if path_prefix is None or not path_prefix:
        return suffix
    return f"{path_prefix}.{suffix}"


def _validate_rule_match(
    rule: object,
    *,
    path_prefix: str,
    issues: list[ValidationIssue],
) -> None:
    match = getattr(rule, "match")
    if match.src_ip is not None and match.src_cidr is not None:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.match",
                code="conflicting_source_match",
                message="src_ip and src_cidr cannot both be set on the same rule",
            )
        )
    if match.dst_ip is not None and match.dst_cidr is not None:
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.match",
                code="conflicting_destination_match",
                message="dst_ip and dst_cidr cannot both be set on the same rule",
            )
        )
    _parse_address(match.src_ip, path=f"{path_prefix}.match.src_ip", issues=issues, optional=True)
    _parse_address(match.dst_ip, path=f"{path_prefix}.match.dst_ip", issues=issues, optional=True)
    _parse_network(match.src_cidr, path=f"{path_prefix}.match.src_cidr", issues=issues, optional=True)
    _parse_network(match.dst_cidr, path=f"{path_prefix}.match.dst_cidr", issues=issues, optional=True)
    if match.proto == "icmp" and (match.src_port is not None or match.dst_port is not None):
        issues.append(
            ValidationIssue(
                path=f"{path_prefix}.match",
                code="icmp_port_match",
                message="icmp rules cannot constrain src_port or dst_port",
            )
        )


def _validate_rule_action(
    action: object,
    *,
    path: str,
    allowed_port_names: Collection[str] | None,
    issues: list[ValidationIssue],
) -> None:
    port_name = getattr(action, "port")
    if port_name is None or allowed_port_names is None:
        return
    if port_name not in allowed_port_names:
        issues.append(
            ValidationIssue(
                path=f"{path}.port",
                code="unknown_port",
                message=f"port '{port_name}' is not declared in dpdk_ports",
            )
        )


def _parse_interface_ref(
    value: str,
    *,
    path: str,
    issues: list[ValidationIssue],
) -> tuple[str, str] | None:
    namespace_name, separator, interface_name = value.partition(":")
    if not separator or not namespace_name or not interface_name:
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_interface_ref",
                message="interface references must use the '<namespace>:<interface>' form",
            )
        )
        return None
    return namespace_name, interface_name


def _parse_interface_address(
    value: str | None,
    *,
    path: str,
    issues: list[ValidationIssue],
) -> ipaddress.IPv4Interface | None:
    if value is None:
        return None
    try:
        interface = ipaddress.ip_interface(value)
    except ValueError:
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_ipv4_interface",
                message=f"'{value}' is not a valid IPv4 interface with prefix length",
            )
        )
        return None
    if not isinstance(interface, ipaddress.IPv4Interface):
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_address_family",
                message="only IPv4 addresses are supported in the MVP",
            )
        )
        return None
    return interface


def _parse_address(
    value: str | None,
    *,
    path: str,
    issues: list[ValidationIssue],
    optional: bool = False,
) -> ipaddress.IPv4Address | None:
    if value is None:
        return None if optional else _missing_value_issue(path, "IPv4 address", issues)
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_ipv4_address",
                message=f"'{value}' is not a valid IPv4 address",
            )
        )
        return None
    if not isinstance(address, ipaddress.IPv4Address):
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_address_family",
                message="only IPv4 addresses are supported in the MVP",
            )
        )
        return None
    return address


def _parse_network(
    value: str | None,
    *,
    path: str,
    issues: list[ValidationIssue],
    optional: bool = False,
) -> ipaddress.IPv4Network | None:
    if value is None:
        return None if optional else _missing_value_issue(path, "IPv4 network with prefix", issues)
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError:
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_ipv4_network",
                message=f"'{value}' is not a valid IPv4 network with prefix length",
            )
        )
        return None
    if not isinstance(network, ipaddress.IPv4Network):
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_address_family",
                message="only IPv4 networks are supported in the MVP",
            )
        )
        return None
    return network


def _missing_value_issue(
    path: str,
    label: str,
    issues: list[ValidationIssue],
) -> None:
    issues.append(
        ValidationIssue(
            path=path,
            code="missing_value",
            message=f"{label} is required",
        )
    )
    return None


def _parse_lcore_spec(
    value: str,
    *,
    path: str,
    issues: list[ValidationIssue],
) -> tuple[int, ...]:
    tokens = [token.strip() for token in value.split(",") if token.strip()]
    if not tokens:
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_lcore_spec",
                message="lcores must contain at least one CPU identifier",
            )
        )
        return (1,)

    parsed: list[int] = []
    for token in tokens:
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            if not start_text.isdigit() or not end_text.isdigit():
                issues.append(
                    ValidationIssue(
                        path=path,
                        code="invalid_lcore_spec",
                        message=f"unsupported lcore token '{token}'",
                    )
                )
                return (1,)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                issues.append(
                    ValidationIssue(
                        path=path,
                        code="invalid_lcore_range",
                        message=f"lcore range '{token}' must be ascending",
                    )
                )
                return (1,)
            parsed.extend(range(start, end + 1))
            continue

        if not token.isdigit():
            issues.append(
                ValidationIssue(
                    path=path,
                    code="invalid_lcore_spec",
                    message=f"unsupported lcore token '{token}'",
                )
            )
            return (1,)
        parsed.append(int(token))

    if len(parsed) != len(set(parsed)):
        issues.append(
            ValidationIssue(
                path=path,
                code="duplicate_lcore",
                message="lcore identifiers must not repeat",
            )
        )
        return tuple(sorted(set(parsed)))

    return tuple(parsed)


def _recommended_hugepages_mb(mempool_size: int) -> int:
    estimated_mbuf_memory_mb = math.ceil(
        mempool_size * MBUF_MEMORY_ESTIMATE_BYTES / (1024 * 1024)
    )
    recommended = DEFAULT_HUGEPAGES_FLOOR_MB
    recommended = max(
        recommended,
        FIXED_RUNTIME_OVERHEAD_MB + estimated_mbuf_memory_mb,
    )
    return _round_up_to_multiple(recommended, DEFAULT_HUGEPAGE_SIZE_MB)


def _round_up_power_of_two(value: int) -> int:
    if value <= 1:
        return 1
    return 1 << (value - 1).bit_length()


def _round_up_to_multiple(value: int, multiple: int) -> int:
    return ((value + multiple - 1) // multiple) * multiple


__all__ = [
    "DEFAULT_BURST_SIZE",
    "DEFAULT_HUGEPAGES_FLOOR_MB",
    "DEFAULT_HUGEPAGE_SIZE_MB",
    "DEFAULT_LCORES",
    "DEFAULT_RX_QUEUE_SIZE",
    "DEFAULT_TX_QUEUE_SIZE",
    "EGRESS_BRIDGE_KERNEL_INTERFACE",
    "INGRESS_BRIDGE_KERNEL_INTERFACE",
    "ValidatedRuleset",
    "ValidatedTopologyConfig",
    "ValidationIssue",
    "derive_effective_dpdk_runtime",
    "validate_ruleset",
    "validate_topology_config",
]
