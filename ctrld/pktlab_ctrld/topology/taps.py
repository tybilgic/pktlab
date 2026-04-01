"""TAP PMD reconciliation helpers for controller-owned topology management."""

from __future__ import annotations

from pktlab_ctrld.config.validation import ValidatedTopologyConfig
from pktlab_ctrld.topology.links import (
    EGRESS_BRIDGE_KERNEL_INTERFACE,
    EGRESS_BRIDGE_NAME,
    INGRESS_BRIDGE_KERNEL_INTERFACE,
    INGRESS_BRIDGE_NAME,
)
from pktlab_ctrld.util.netns import NetnsRunner
from pktlab_ctrld.util.time import wait_until


def reconcile_taps(
    topology: ValidatedTopologyConfig,
    *,
    netns: NetnsRunner,
    timeout_seconds: float = 5.0,
    poll_interval_seconds: float = 0.05,
) -> None:
    """Wait for datapath-created TAP interfaces, bridge them, and bring them up."""

    dpdk_namespace = topology.requested_dpdk_config.namespace
    ingress_port_name = _port_name_for_role(topology, "ingress")
    egress_port_name = _port_name_for_role(topology, "egress")

    for interface_name in (ingress_port_name, egress_port_name):
        wait_until(
            lambda interface_name=interface_name: netns.link_exists(dpdk_namespace, interface_name),
            description=f"{interface_name} in namespace {dpdk_namespace}",
            timeout_seconds=timeout_seconds,
            interval_seconds=poll_interval_seconds,
        )

    netns.attach_to_bridge(
        namespace=dpdk_namespace,
        interface=INGRESS_BRIDGE_KERNEL_INTERFACE,
        bridge=INGRESS_BRIDGE_NAME,
    )
    netns.attach_to_bridge(
        namespace=dpdk_namespace,
        interface=ingress_port_name,
        bridge=INGRESS_BRIDGE_NAME,
    )
    netns.attach_to_bridge(
        namespace=dpdk_namespace,
        interface=egress_port_name,
        bridge=EGRESS_BRIDGE_NAME,
    )
    netns.attach_to_bridge(
        namespace=dpdk_namespace,
        interface=EGRESS_BRIDGE_KERNEL_INTERFACE,
        bridge=EGRESS_BRIDGE_NAME,
    )

    for interface_name in (
        INGRESS_BRIDGE_KERNEL_INTERFACE,
        ingress_port_name,
        egress_port_name,
        EGRESS_BRIDGE_KERNEL_INTERFACE,
        INGRESS_BRIDGE_NAME,
        EGRESS_BRIDGE_NAME,
    ):
        netns.set_link_up(namespace=dpdk_namespace, interface=interface_name)


def _port_name_for_role(topology: ValidatedTopologyConfig, role: str) -> str:
    for port in topology.topology.dpdk_ports:
        if port.role == role:
            return port.name
    raise ValueError(f"expected a dpdk port with role {role}")


__all__ = ["reconcile_taps"]
