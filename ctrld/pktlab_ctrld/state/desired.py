"""Desired controller state models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ControllerStateValue = Literal[
    "stopped",
    "starting",
    "running",
    "degraded",
    "reconciling",
    "stopping",
    "failed",
]


def _validate_optional_text(field_name: str, value: str | None) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string when provided")


@dataclass(frozen=True, slots=True)
class DesiredState:
    """State the controller wants the lab to converge toward."""

    topology_config_path: str | None = None
    topology_name: str | None = None
    desired_rules_version: int | None = None
    desired_controller_state: ControllerStateValue = "stopped"
    desired_datapath_running: bool = False

    def __post_init__(self) -> None:
        _validate_optional_text("topology_config_path", self.topology_config_path)
        _validate_optional_text("topology_name", self.topology_name)
        if self.desired_rules_version is not None and self.desired_rules_version < 0:
            raise ValueError("desired_rules_version must be non-negative")

    @property
    def topology_requested(self) -> bool:
        """Return whether the desired state expects a topology to exist."""

        return self.topology_name is not None

__all__ = ["ControllerStateValue", "DesiredState"]
