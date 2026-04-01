"""Shared external-facing models for pktlab controller code."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ControllerState = Literal[
    "stopped",
    "starting",
    "running",
    "degraded",
    "reconciling",
    "stopping",
    "failed",
]

DatapathState = Literal[
    "starting",
    "running",
    "paused",
    "degraded",
    "stopping",
    "failed",
]

RuleProtocol = Literal["tcp", "udp", "icmp", "any"]
RuleActionType = Literal["forward", "drop", "count", "mirror"]
PortRole = Literal["ingress", "egress"]


class RuleMatchModel(BaseModel):
    """Rule match model shared by config and IPC payloads."""

    model_config = ConfigDict(extra="forbid")

    proto: RuleProtocol | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    src_cidr: str | None = None
    dst_cidr: str | None = None
    src_port: int | None = Field(default=None, ge=0, le=65535)
    dst_port: int | None = Field(default=None, ge=0, le=65535)


class RuleActionModel(BaseModel):
    """Rule action model shared by config and IPC payloads."""

    model_config = ConfigDict(extra="forbid")

    type: RuleActionType
    port: str | None = None

    @model_validator(mode="after")
    def validate_port_requirement(self) -> "RuleActionModel":
        if self.type in {"forward", "mirror"} and not self.port:
            raise ValueError("port is required for forward and mirror actions")
        if self.type in {"drop", "count"} and self.port is not None:
            raise ValueError("port must be omitted for drop and count actions")
        return self


class RuleModel(BaseModel):
    """Single rule definition."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=0)
    priority: int = Field(ge=0)
    match: RuleMatchModel
    action: RuleActionModel


class RulesetModel(BaseModel):
    """Ruleset model for topology config input."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=0)
    default_action: RuleActionModel
    entries: list[RuleModel] = Field(default_factory=list)


class CapturePointModel(BaseModel):
    """Named capture point definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    interface: str = Field(min_length=1)


class LabModel(BaseModel):
    """Top-level lab metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)


class NamespaceModel(BaseModel):
    """Namespace declaration from topology config."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)


class LinkModel(BaseModel):
    """Point-to-point veth link description."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    a: str = Field(min_length=1)
    b: str = Field(min_length=1)
    ip_a: str | None = None
    ip_b: str | None = None


class DpdkPortModel(BaseModel):
    """Controller-visible datapath port definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    role: PortRole


class RouteModel(BaseModel):
    """Static route declaration."""

    model_config = ConfigDict(extra="forbid")

    namespace: str = Field(min_length=1)
    dst: str = Field(min_length=1)
    via: str = Field(min_length=1)


class DpdkProcessConfigModel(BaseModel):
    """Resource-aware datapath process configuration."""

    model_config = ConfigDict(extra="forbid")

    namespace: str = Field(min_length=1)
    lcores: str | None = None
    hugepages_mb: int | None = Field(default=None, ge=2)
    burst_size: int | None = Field(default=None, ge=1)
    rx_queue_size: int | None = Field(default=None, ge=1)
    tx_queue_size: int | None = Field(default=None, ge=1)
    mempool_size: int | None = Field(default=None, ge=1)


class EffectiveDpdkRuntimeModel(BaseModel):
    """Resolved datapath runtime configuration after controller defaults are applied."""

    model_config = ConfigDict(extra="forbid")

    lcores: str = Field(min_length=1)
    lcore_count: int = Field(ge=1)
    hugepage_size_mb: Literal[2] = 2
    hugepages_mb: int = Field(ge=2, multiple_of=2)
    burst_size: int = Field(ge=1)
    rx_queue_size: int = Field(ge=1)
    tx_queue_size: int = Field(ge=1)
    mempool_size: int = Field(ge=1)
    port_count: int = Field(ge=1)


class ControllerProcessConfigModel(BaseModel):
    """Controller process listen configuration."""

    model_config = ConfigDict(extra="forbid")

    rest_listen: str | None = None
    metrics_listen: str | None = None


class ProcessesModel(BaseModel):
    """Configured process set for a topology."""

    model_config = ConfigDict(extra="forbid")

    dpdkd: DpdkProcessConfigModel
    ctrld: ControllerProcessConfigModel | None = None


class TopologyConfigModel(BaseModel):
    """Full topology configuration document."""

    model_config = ConfigDict(extra="forbid")

    lab: LabModel
    processes: ProcessesModel
    namespaces: list[NamespaceModel]
    links: list[LinkModel]
    dpdk_ports: list[DpdkPortModel]
    routes: list[RouteModel]
    rules: RulesetModel
    capture_points: list[CapturePointModel]


__all__ = [
    "CapturePointModel",
    "ControllerProcessConfigModel",
    "ControllerState",
    "DatapathState",
    "EffectiveDpdkRuntimeModel",
    "DpdkPortModel",
    "DpdkProcessConfigModel",
    "LabModel",
    "LinkModel",
    "NamespaceModel",
    "PortRole",
    "ProcessesModel",
    "RouteModel",
    "RuleActionModel",
    "RuleActionType",
    "RuleMatchModel",
    "RuleModel",
    "RuleProtocol",
    "RulesetModel",
    "TopologyConfigModel",
]
