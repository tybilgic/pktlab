"""Namespace lifecycle helpers for controller-owned topology management."""

from __future__ import annotations

from pktlab_ctrld.config.validation import ValidatedTopologyConfig
from pktlab_ctrld.util.netns import NetnsRunner


def ensure_namespaces(topology: ValidatedTopologyConfig, *, netns: NetnsRunner) -> None:
    """Create all namespaces declared by the topology."""

    for namespace in topology.topology.namespaces:
        netns.ensure_namespace(namespace.name)


def destroy_namespaces(topology: ValidatedTopologyConfig, *, netns: NetnsRunner) -> None:
    """Delete all namespaces declared by the topology in reverse order."""

    for namespace in reversed(topology.topology.namespaces):
        netns.delete_namespace(namespace.name)


__all__ = ["destroy_namespaces", "ensure_namespaces"]
