"""Unit tests for desired/observed state reconciliation."""

from __future__ import annotations

import unittest

from pktlab_ctrld.state import (
    CaptureObservation,
    DesiredState,
    ObservedState,
    ReconcileActionType,
    build_reconcile_plan,
)


class StateReconcileTests(unittest.TestCase):
    """Keep reconcile ordering deterministic and explicit."""

    def test_plan_orders_apply_start_and_rules_sync(self) -> None:
        desired = DesiredState(
            topology_name="linear-basic",
            topology_config_path="lab/topology.yaml",
            desired_rules_version=3,
            desired_controller_state="running",
            desired_datapath_running=True,
        )
        observed = ObservedState(
            datapath_health=None,
            applied_rules_version=2,
            dpdkd_pid=None,
            topology_applied=False,
        )

        plan = build_reconcile_plan(desired, observed)

        self.assertEqual(
            [action.action for action in plan.actions],
            [
                ReconcileActionType.APPLY_TOPOLOGY,
                ReconcileActionType.START_DATAPATH,
                ReconcileActionType.REPLACE_RULES,
            ],
        )

    def test_plan_orders_stop_before_destroy(self) -> None:
        desired = DesiredState(
            desired_controller_state="stopped",
            desired_datapath_running=False,
        )
        observed = ObservedState(
            datapath_health="running",
            applied_rules_version=7,
            dpdkd_pid=4242,
            topology_applied=True,
        )

        plan = build_reconcile_plan(desired, observed)

        self.assertEqual(
            [action.action for action in plan.actions],
            [
                ReconcileActionType.STOP_DATAPATH,
                ReconcileActionType.DESTROY_TOPOLOGY,
            ],
        )

    def test_observed_captures_are_copied_into_an_immutable_mapping(self) -> None:
        capture = CaptureObservation(namespace="tg-src", interface="eth0", pid=1234)
        observed = ObservedState(active_captures={"src": capture})

        self.assertEqual(observed.active_captures["src"], capture)
        with self.assertRaises(TypeError):
            observed.active_captures["sink"] = capture  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
