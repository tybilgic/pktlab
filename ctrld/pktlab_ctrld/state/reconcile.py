"""Deterministic state reconciliation planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .desired import DesiredState
from .observed import ObservedState


class ReconcileActionType(StrEnum):
    """High-level reconciliation actions computed from desired/observed state."""

    STOP_DATAPATH = "stop_datapath"
    DESTROY_TOPOLOGY = "destroy_topology"
    APPLY_TOPOLOGY = "apply_topology"
    START_DATAPATH = "start_datapath"
    WAIT_FOR_DATAPATH = "wait_for_datapath"
    REPLACE_RULES = "replace_rules"


@dataclass(frozen=True, slots=True)
class ReconcileAction:
    """One planned reconciliation action."""

    action: ReconcileActionType
    reason: str


@dataclass(frozen=True, slots=True)
class ReconcilePlan:
    """Ordered list of actions required to move toward the desired state."""

    actions: tuple[ReconcileAction, ...] = ()

    @property
    def is_noop(self) -> bool:
        """Return whether no reconciliation is needed."""

        return not self.actions


def build_reconcile_plan(desired: DesiredState, observed: ObservedState) -> ReconcilePlan:
    """Compute an ordered, side-effect-free reconcile plan."""

    actions: list[ReconcileAction] = []

    if not desired.desired_datapath_running and observed.datapath_running:
        actions.append(
            ReconcileAction(
                ReconcileActionType.STOP_DATAPATH,
                "datapath is running but the desired state does not require it",
            )
        )

    if not desired.topology_requested and observed.topology_applied:
        actions.append(
            ReconcileAction(
                ReconcileActionType.DESTROY_TOPOLOGY,
                "topology is applied but the desired state no longer requests one",
            )
        )

    if desired.topology_requested and not observed.topology_applied:
        actions.append(
            ReconcileAction(
                ReconcileActionType.APPLY_TOPOLOGY,
                "desired topology is missing from the observed state",
            )
        )

    if desired.desired_datapath_running and not observed.datapath_running:
        actions.append(
            ReconcileAction(
                ReconcileActionType.START_DATAPATH,
                "desired state requires the datapath process to be running",
            )
        )

    if (
        desired.desired_datapath_running
        and observed.datapath_running
        and observed.datapath_health != "running"
    ):
        actions.append(
            ReconcileAction(
                ReconcileActionType.WAIT_FOR_DATAPATH,
                "datapath process exists but has not reported a healthy running state yet",
            )
        )

    if (
        desired.desired_rules_version is not None
        and desired.desired_rules_version != observed.applied_rules_version
    ):
        actions.append(
            ReconcileAction(
                ReconcileActionType.REPLACE_RULES,
                "observed datapath rules do not match the desired rules version",
            )
        )

    return ReconcilePlan(actions=tuple(actions))


__all__ = [
    "ReconcileAction",
    "ReconcileActionType",
    "ReconcilePlan",
    "build_reconcile_plan",
]
