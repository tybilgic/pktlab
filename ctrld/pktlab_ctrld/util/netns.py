"""Namespace-aware wrappers around Linux `ip` tooling."""

from __future__ import annotations

from typing import Sequence

from .subprocess import CommandExecutor, CommandResult


class NetnsRunner:
    """Run namespace and link operations through the centralized command executor."""

    def __init__(self, executor: CommandExecutor | None = None) -> None:
        self._executor = executor or CommandExecutor()

    def run_ip(
        self,
        *arguments: str,
        namespace: str | None = None,
        allowed_returncodes: Sequence[int] = (0,),
    ) -> CommandResult:
        argv = ["ip"]
        if namespace is not None:
            argv.extend(["-n", namespace])
        argv.extend(arguments)
        return self._executor.run(argv, allowed_returncodes=allowed_returncodes)

    def list_namespaces(self) -> tuple[str, ...]:
        """Return the currently visible network namespace names."""

        result = self.run_ip("netns", "list")
        namespaces: list[str] = []
        for line in result.stdout.splitlines():
            tokens = line.split()
            if tokens:
                namespaces.append(tokens[0])
        return tuple(namespaces)

    def namespace_exists(self, namespace: str) -> bool:
        """Return whether a named network namespace exists."""

        return namespace in set(self.list_namespaces())

    def ensure_namespace(self, namespace: str) -> None:
        """Create a network namespace if it is not already present."""

        if self.namespace_exists(namespace):
            return
        self.run_ip("netns", "add", namespace)

    def delete_namespace(self, namespace: str) -> None:
        """Delete a network namespace if it is present."""

        if not self.namespace_exists(namespace):
            return
        self.run_ip("netns", "del", namespace)

    def link_exists(self, namespace: str, interface: str) -> bool:
        """Return whether an interface exists within a namespace."""

        result = self.run_ip(
            "link",
            "show",
            "dev",
            interface,
            namespace=namespace,
            allowed_returncodes=(0, 1),
        )
        return result.returncode == 0

    def ensure_veth_pair(
        self,
        *,
        namespace_a: str,
        interface_a: str,
        namespace_b: str,
        interface_b: str,
    ) -> None:
        """Create a veth pair directly into the target namespaces if missing."""

        if self.link_exists(namespace_a, interface_a) and self.link_exists(namespace_b, interface_b):
            return
        self.run_ip(
            "link",
            "add",
            "name",
            interface_a,
            "netns",
            namespace_a,
            "type",
            "veth",
            "peer",
            "name",
            interface_b,
            "netns",
            namespace_b,
        )

    def delete_link(self, *, namespace: str, interface: str) -> None:
        """Delete an interface if it is present inside a namespace."""

        if not self.link_exists(namespace, interface):
            return
        self.run_ip("link", "del", "dev", interface, namespace=namespace)

    def ensure_bridge(self, *, namespace: str, bridge: str) -> None:
        """Create a Linux bridge inside the namespace if it is not already present."""

        if self.link_exists(namespace, bridge):
            return
        self.run_ip("link", "add", "name", bridge, "type", "bridge", namespace=namespace)

    def replace_address(self, *, namespace: str, interface: str, cidr: str) -> None:
        """Ensure an interface has the given IPv4 address."""

        self.run_ip("address", "replace", cidr, "dev", interface, namespace=namespace)

    def replace_route(self, *, namespace: str, dst: str, via: str) -> None:
        """Ensure a namespace has the given static route."""

        self.run_ip("route", "replace", dst, "via", via, namespace=namespace)

    def attach_to_bridge(self, *, namespace: str, interface: str, bridge: str) -> None:
        """Attach an interface to a Linux bridge."""

        self.run_ip("link", "set", "dev", interface, "master", bridge, namespace=namespace)

    def set_link_up(self, *, namespace: str, interface: str) -> None:
        """Bring an interface up inside the namespace."""

        self.run_ip("link", "set", "dev", interface, "up", namespace=namespace)


__all__ = ["NetnsRunner"]
