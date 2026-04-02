"""Serialized topology orchestration for controller-owned lab lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable, Literal

from pktlab_ctrld.config.topology import load_topology_config
from pktlab_ctrld.config.validation import ValidatedTopologyConfig, validate_topology_config
from pktlab_ctrld.error import ErrorCode, PktlabError
from pktlab_ctrld.process.supervisor import DatapathProcessStatus
from pktlab_ctrld.topology.links import bring_link_endpoints_up, destroy_links_and_bridges, ensure_bridges, ensure_links
from pktlab_ctrld.topology.namespaces import destroy_namespaces, ensure_namespaces
from pktlab_ctrld.topology.routes import ensure_routes
from pktlab_ctrld.topology.taps import reconcile_taps
from pktlab_ctrld.types import DpdkProcessConfigModel, EffectiveDpdkRuntimeModel
from pktlab_ctrld.util.netns import NetnsRunner

TopologyOperation = Literal["apply", "destroy"]


@dataclass(frozen=True, slots=True)
class TopologyOperationResult:
    """User-visible result of a topology lifecycle operation."""

    operation: TopologyOperation
    topology_name: str | None
    config_path: str | None
    applied: bool
    datapath_namespace: str | None
    datapath_running: bool
    message: str
    requested_dpdk_config: DpdkProcessConfigModel | None = None
    effective_dpdk_config: EffectiveDpdkRuntimeModel | None = None


@dataclass(frozen=True, slots=True)
class _AppliedTopology:
    """Internal record of the currently applied topology."""

    config_path: str
    validated: ValidatedTopologyConfig


class TopologyManager:
    """Apply and destroy controller-owned lab topology in a serialized way."""

    def __init__(
        self,
        *,
        netns: NetnsRunner | None = None,
        load_topology: Callable[[str], object] = load_topology_config,
        validate_topology: Callable[[object], ValidatedTopologyConfig] = validate_topology_config,
        start_datapath: Callable[[ValidatedTopologyConfig], DatapathProcessStatus] | None = None,
        stop_datapath: Callable[[], None] | None = None,
        tap_timeout_seconds: float = 5.0,
        tap_poll_interval_seconds: float = 0.05,
    ) -> None:
        self._netns = netns or NetnsRunner()
        self._load_topology = load_topology
        self._validate_topology = validate_topology
        self._start_datapath = start_datapath
        self._stop_datapath = stop_datapath
        self._tap_timeout_seconds = tap_timeout_seconds
        self._tap_poll_interval_seconds = tap_poll_interval_seconds
        self._lock = RLock()
        self._current: _AppliedTopology | None = None

    @property
    def has_applied_topology(self) -> bool:
        """Return whether a topology is currently considered active."""

        return self._current is not None

    def apply(self, config_path: str) -> TopologyOperationResult:
        """Apply a topology from a YAML document path."""

        with self._lock:
            loaded = self._load_topology(config_path)
            validated = self._validate_topology(loaded)

            current = self._current
            if current is not None:
                self._destroy_locked(current.validated)
                self._current = None

            try:
                ensure_namespaces(validated, netns=self._netns)
                ensure_links(validated, netns=self._netns)
                ensure_bridges(validated, netns=self._netns)
                ensure_routes(validated, netns=self._netns)
                datapath_status = self._start_datapath_locked(validated)
                reconcile_taps(
                    validated,
                    netns=self._netns,
                    timeout_seconds=self._tap_timeout_seconds,
                    poll_interval_seconds=self._tap_poll_interval_seconds,
                )
                bring_link_endpoints_up(validated, netns=self._netns)
            except Exception as exc:
                cleanup_error = self._cleanup_failed_apply(validated)
                if isinstance(exc, PktlabError):
                    if cleanup_error is None:
                        raise
                    raise self._merge_cleanup_error(exc, cleanup_error) from exc
                context = {
                    "config_path": config_path,
                    "topology_name": validated.topology.lab.name,
                    "detail": str(exc),
                }
                if cleanup_error is not None:
                    context["cleanup_error"] = cleanup_error.to_dict()
                raise PktlabError(
                    ErrorCode.TOPOLOGY_APPLY_ERROR,
                    "failed to apply topology",
                    context=context,
                ) from exc

            self._current = _AppliedTopology(config_path=config_path, validated=validated)
            return self._result(
                operation="apply",
                validated=validated,
                config_path=config_path,
                applied=True,
                datapath_running=datapath_status.running,
                message="topology applied",
            )

    def destroy(self) -> TopologyOperationResult:
        """Destroy the currently applied topology if one exists."""

        with self._lock:
            current = self._current
            if current is None:
                return TopologyOperationResult(
                    operation="destroy",
                    topology_name=None,
                    config_path=None,
                    applied=False,
                    datapath_namespace=None,
                    datapath_running=False,
                    message="no topology is currently applied",
                )

            validated = current.validated
            config_path = current.config_path
            self._destroy_locked(validated)
            self._current = None
            return self._result(
                operation="destroy",
                validated=validated,
                config_path=config_path,
                applied=False,
                datapath_running=False,
                message="topology destroyed",
            )

    def _destroy_locked(self, validated: ValidatedTopologyConfig) -> None:
        errors: list[PktlabError] = []
        try:
            self._stop_datapath_locked()
        except PktlabError as exc:
            errors.append(exc)

        try:
            destroy_links_and_bridges(validated, netns=self._netns)
        except PktlabError as exc:
            errors.append(exc)

        try:
            destroy_namespaces(validated, netns=self._netns)
        except PktlabError as exc:
            errors.append(exc)

        if errors:
            raise PktlabError(
                ErrorCode.TOPOLOGY_DESTROY_ERROR,
                "failed to destroy topology cleanly",
                context={
                    "topology_name": validated.topology.lab.name,
                    "errors": [error.to_dict() for error in errors],
                },
            )

    def _cleanup_failed_apply(self, validated: ValidatedTopologyConfig) -> PktlabError | None:
        try:
            self._destroy_locked(validated)
        except PktlabError as exc:
            return exc
        return None

    def _merge_cleanup_error(self, error: PktlabError, cleanup_error: PktlabError) -> PktlabError:
        context = dict(error.context)
        context["cleanup_error"] = cleanup_error.to_dict()
        return PktlabError(
            error.code,
            error.message,
            context=context or None,
        )

    def _start_datapath_locked(self, validated: ValidatedTopologyConfig) -> DatapathProcessStatus:
        if self._start_datapath is None:
            raise PktlabError(
                ErrorCode.STATE_CONFLICT,
                "topology manager cannot start pktlab-dpdkd because no datapath start callback is configured",
            )
        return self._start_datapath(validated)

    def _stop_datapath_locked(self) -> None:
        if self._stop_datapath is not None:
            self._stop_datapath()

    def _result(
        self,
        *,
        operation: TopologyOperation,
        validated: ValidatedTopologyConfig,
        config_path: str,
        applied: bool,
        datapath_running: bool,
        message: str,
    ) -> TopologyOperationResult:
        return TopologyOperationResult(
            operation=operation,
            topology_name=validated.topology.lab.name,
            config_path=config_path,
            applied=applied,
            datapath_namespace=validated.requested_dpdk_config.namespace,
            datapath_running=datapath_running,
            message=message,
            requested_dpdk_config=validated.requested_dpdk_config,
            effective_dpdk_config=validated.effective_dpdk_config,
        )


__all__ = ["TopologyManager", "TopologyOperationResult"]
