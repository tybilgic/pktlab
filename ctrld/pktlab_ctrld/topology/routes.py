"""Static route lifecycle helpers for controller-owned topology management."""

from __future__ import annotations

from pktlab_ctrld.config.validation import ValidatedTopologyConfig
from pktlab_ctrld.util.netns import NetnsRunner


def ensure_routes(topology: ValidatedTopologyConfig, *, netns: NetnsRunner) -> None:
    """Program static routes declared by the topology."""

    for route in topology.topology.routes:
        netns.replace_route(namespace=route.namespace, dst=route.dst, via=route.via)


__all__ = ["ensure_routes"]
