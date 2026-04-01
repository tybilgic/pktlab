"""Link and bridge lifecycle helpers for controller-owned topology management."""

from __future__ import annotations

from pktlab_ctrld.config.validation import ValidatedTopologyConfig
from pktlab_ctrld.util.netns import NetnsRunner

INGRESS_BRIDGE_NAME = "br-in"
EGRESS_BRIDGE_NAME = "br-out"
INGRESS_BRIDGE_KERNEL_INTERFACE = "veth-in-k"
EGRESS_BRIDGE_KERNEL_INTERFACE = "veth-out-k"


def ensure_links(topology: ValidatedTopologyConfig, *, netns: NetnsRunner) -> None:
    """Create the veth links declared by the topology and apply interface addresses."""

    for link in topology.topology.links:
        namespace_a, interface_a = _split_ref(link.a)
        namespace_b, interface_b = _split_ref(link.b)
        netns.ensure_veth_pair(
            namespace_a=namespace_a,
            interface_a=interface_a,
            namespace_b=namespace_b,
            interface_b=interface_b,
        )
        if link.ip_a is not None:
            netns.replace_address(namespace=namespace_a, interface=interface_a, cidr=link.ip_a)
        if link.ip_b is not None:
            netns.replace_address(namespace=namespace_b, interface=interface_b, cidr=link.ip_b)


def ensure_bridges(topology: ValidatedTopologyConfig, *, netns: NetnsRunner) -> None:
    """Create the controller-owned Linux bridges inside the datapath namespace."""

    dpdk_namespace = topology.requested_dpdk_config.namespace
    netns.ensure_bridge(namespace=dpdk_namespace, bridge=INGRESS_BRIDGE_NAME)
    netns.ensure_bridge(namespace=dpdk_namespace, bridge=EGRESS_BRIDGE_NAME)


def bring_link_endpoints_up(topology: ValidatedTopologyConfig, *, netns: NetnsRunner) -> None:
    """Bring all topology link interfaces up after bridge reconciliation."""

    for link in topology.topology.links:
        namespace_a, interface_a = _split_ref(link.a)
        namespace_b, interface_b = _split_ref(link.b)
        netns.set_link_up(namespace=namespace_a, interface=interface_a)
        netns.set_link_up(namespace=namespace_b, interface=interface_b)


def destroy_links_and_bridges(topology: ValidatedTopologyConfig, *, netns: NetnsRunner) -> None:
    """Delete bridges first, then veth links, in reverse topology order."""

    dpdk_namespace = topology.requested_dpdk_config.namespace
    for bridge in (EGRESS_BRIDGE_NAME, INGRESS_BRIDGE_NAME):
        netns.delete_link(namespace=dpdk_namespace, interface=bridge)

    for link in reversed(topology.topology.links):
        namespace_a, interface_a = _split_ref(link.a)
        netns.delete_link(namespace=namespace_a, interface=interface_a)


def _split_ref(value: str) -> tuple[str, str]:
    namespace, _, interface = value.partition(":")
    return namespace, interface


__all__ = [
    "EGRESS_BRIDGE_KERNEL_INTERFACE",
    "EGRESS_BRIDGE_NAME",
    "INGRESS_BRIDGE_KERNEL_INTERFACE",
    "INGRESS_BRIDGE_NAME",
    "bring_link_endpoints_up",
    "destroy_links_and_bridges",
    "ensure_bridges",
    "ensure_links",
]
