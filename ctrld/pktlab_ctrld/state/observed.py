"""Observed runtime state models."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Mapping

DatapathStateValue = Literal[
    "starting",
    "running",
    "paused",
    "degraded",
    "stopping",
    "failed",
]


def _validate_optional_non_negative(field_name: str, value: int | None) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_optional_positive(field_name: str, value: int | None) -> None:
    if value is not None and value <= 0:
        raise ValueError(f"{field_name} must be greater than zero when provided")


@dataclass(frozen=True, slots=True)
class CaptureObservation:
    """Minimal runtime capture state tracked by the controller."""

    namespace: str
    interface: str
    pid: int | None = None

    def __post_init__(self) -> None:
        if not self.namespace.strip():
            raise ValueError("namespace must be a non-empty string")
        if not self.interface.strip():
            raise ValueError("interface must be a non-empty string")
        _validate_optional_positive("pid", self.pid)


@dataclass(frozen=True, slots=True)
class ObservedState:
    """State observed from the live system and supervised processes."""

    datapath_health: DatapathStateValue | None = None
    applied_rules_version: int | None = None
    dpdkd_pid: int | None = None
    active_captures: Mapping[str, CaptureObservation] = field(default_factory=dict)
    topology_applied: bool = False

    def __post_init__(self) -> None:
        _validate_optional_non_negative("applied_rules_version", self.applied_rules_version)
        _validate_optional_positive("dpdkd_pid", self.dpdkd_pid)
        object.__setattr__(
            self,
            "active_captures",
            MappingProxyType(dict(self.active_captures)),
        )

    @property
    def datapath_running(self) -> bool:
        """Return whether a datapath process is currently present."""

        return self.dpdkd_pid is not None

__all__ = ["CaptureObservation", "DatapathStateValue", "ObservedState"]
