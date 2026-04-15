"""Controller-facing REST API models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pktlab_ctrld.types import ControllerState, DatapathState


class ControllerHealthModel(BaseModel):
    """Controller service health payload."""

    model_config = ConfigDict(extra="forbid")

    service: Literal["pktlab-ctrld"] = "pktlab-ctrld"
    version: str = Field(min_length=1)
    state: ControllerState
    message: str = Field(min_length=1)


class DatapathHealthModel(BaseModel):
    """Datapath section of the controller health response."""

    model_config = ConfigDict(extra="forbid")

    managed: bool
    reachable: bool
    socket_path: str = Field(min_length=1)
    pid: int | None = Field(default=None, ge=1)
    exit_code: int | None = None
    last_error: str | None = None
    service: Literal["pktlab-dpdkd"] | None = None
    version: str | None = None
    dpdk_version: str | None = None
    state: DatapathState | None = None
    message: str | None = None
    applied_rule_version: int | None = Field(default=None, ge=0)
    ports_ready: bool = False
    paused: bool = False


class DatapathPortModel(BaseModel):
    """Single datapath port status entry."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    port_id: int = Field(ge=0)
    role: Literal["ingress", "egress"]
    state: Literal["up", "down"]


class DatapathStatsModel(BaseModel):
    """Controller-facing datapath counters."""

    model_config = ConfigDict(extra="forbid")

    rx_packets: int = Field(ge=0)
    tx_packets: int = Field(ge=0)
    drop_packets: int = Field(ge=0)
    drop_parse_errors: int = Field(ge=0)
    drop_no_match: int = Field(ge=0)
    rx_bursts: int = Field(ge=0)
    tx_bursts: int = Field(ge=0)
    unsent_packets: int = Field(ge=0)
    rule_hits: dict[str, int] = Field(default_factory=dict)


def _datapath_health_model_from_status(datapath_status: object) -> DatapathHealthModel:
    """Map a supervisor status object into the public datapath health model."""

    from pktlab_ctrld.process.supervisor import DatapathProcessStatus

    if not isinstance(datapath_status, DatapathProcessStatus):
        raise TypeError("datapath_status must be a DatapathProcessStatus")

    datapath_health = datapath_status.health
    datapath_version = datapath_status.version
    return DatapathHealthModel(
        managed=datapath_status.managed,
        reachable=datapath_status.reachable,
        socket_path=datapath_status.socket_path,
        pid=datapath_status.pid,
        exit_code=datapath_status.exit_code,
        last_error=datapath_status.last_error,
        service=datapath_version.service if datapath_version is not None else None,
        version=datapath_version.version if datapath_version is not None else None,
        dpdk_version=datapath_version.dpdk_version if datapath_version is not None else None,
        state=datapath_health.state if datapath_health is not None else None,
        message=datapath_health.message if datapath_health is not None else None,
        applied_rule_version=(
            datapath_health.applied_rule_version if datapath_health is not None else None
        ),
        ports_ready=datapath_health.ports_ready if datapath_health is not None else False,
        paused=datapath_health.paused if datapath_health is not None else False,
    )


class HealthResponseModel(BaseModel):
    """Top-level controller health response."""

    model_config = ConfigDict(extra="forbid")

    controller: ControllerHealthModel
    datapath: DatapathHealthModel

    @classmethod
    def from_snapshot(cls, snapshot: object) -> "HealthResponseModel":
        """Map an internal health snapshot into the REST response model."""

        from pktlab_ctrld.app import ControllerHealthSnapshot

        if not isinstance(snapshot, ControllerHealthSnapshot):
            raise TypeError("snapshot must be a ControllerHealthSnapshot")

        return cls(
            controller=ControllerHealthModel(
                version=snapshot.controller_version,
                state=snapshot.controller_state,
                message=snapshot.controller_message,
            ),
            datapath=_datapath_health_model_from_status(snapshot.datapath_status),
        )


class DatapathStatusResponseModel(BaseModel):
    """Controller-facing datapath status including ports."""

    model_config = ConfigDict(extra="forbid")

    controller: ControllerHealthModel
    datapath: DatapathHealthModel
    ports: list[DatapathPortModel]

    @classmethod
    def from_snapshot(cls, snapshot: object) -> "DatapathStatusResponseModel":
        """Map an internal datapath status snapshot into the REST model."""

        from pktlab_ctrld.app import DatapathRuntimeStatusSnapshot

        if not isinstance(snapshot, DatapathRuntimeStatusSnapshot):
            raise TypeError("snapshot must be a DatapathRuntimeStatusSnapshot")

        health = HealthResponseModel.from_snapshot(snapshot.controller_snapshot)
        return cls(
            controller=health.controller,
            datapath=health.datapath,
            ports=[
                DatapathPortModel(
                    name=port.name,
                    port_id=port.port_id,
                    role=port.role,
                    state=port.state,
                )
                for port in snapshot.ports
            ],
        )


class DatapathStatsResponseModel(BaseModel):
    """Controller-facing datapath counters with runtime status."""

    model_config = ConfigDict(extra="forbid")

    datapath: DatapathHealthModel
    stats: DatapathStatsModel

    @classmethod
    def from_snapshot(cls, snapshot: object) -> "DatapathStatsResponseModel":
        """Map an internal datapath stats snapshot into the REST model."""

        from pktlab_ctrld.app import DatapathRuntimeStatsSnapshot

        if not isinstance(snapshot, DatapathRuntimeStatsSnapshot):
            raise TypeError("snapshot must be a DatapathRuntimeStatsSnapshot")

        return cls(
            datapath=_datapath_health_model_from_status(snapshot.datapath_status),
            stats=DatapathStatsModel.model_validate(snapshot.stats.model_dump(mode="json")),
        )


class DatapathStatsResetResponseModel(BaseModel):
    """Controller-facing datapath stats reset result."""

    model_config = ConfigDict(extra="forbid")

    datapath: DatapathHealthModel
    stats: DatapathStatsModel
    message: str = Field(min_length=1)

    @classmethod
    def from_result(cls, result: object) -> "DatapathStatsResetResponseModel":
        """Map an internal datapath stats reset result into the REST model."""

        from pktlab_ctrld.app import DatapathStatsResetResult

        if not isinstance(result, DatapathStatsResetResult):
            raise TypeError("result must be a DatapathStatsResetResult")

        return cls(
            datapath=_datapath_health_model_from_status(result.datapath_status),
            stats=DatapathStatsModel.model_validate(result.stats.model_dump(mode="json")),
            message=result.message,
        )


class TopologyApplyRequestModel(BaseModel):
    """Request body for topology apply."""

    model_config = ConfigDict(extra="forbid")

    config_path: str = Field(min_length=1)


class TopologyOperationResponseModel(BaseModel):
    """Response body for topology apply/destroy operations."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["apply", "destroy"]
    topology_name: str | None = None
    config_path: str | None = None
    applied: bool
    datapath_namespace: str | None = None
    datapath_running: bool
    message: str = Field(min_length=1)

    @classmethod
    def from_result(cls, result: object) -> "TopologyOperationResponseModel":
        """Map a topology manager result into the REST response model."""

        from pktlab_ctrld.topology.manager import TopologyOperationResult

        if not isinstance(result, TopologyOperationResult):
            raise TypeError("result must be a TopologyOperationResult")

        return cls(
            operation=result.operation,
            topology_name=result.topology_name,
            config_path=result.config_path,
            applied=result.applied,
            datapath_namespace=result.datapath_namespace,
            datapath_running=result.datapath_running,
            message=result.message,
        )


__all__ = [
    "ControllerHealthModel",
    "DatapathHealthModel",
    "DatapathPortModel",
    "DatapathStatsResetResponseModel",
    "DatapathStatsModel",
    "DatapathStatsResponseModel",
    "DatapathStatusResponseModel",
    "HealthResponseModel",
    "TopologyApplyRequestModel",
    "TopologyOperationResponseModel",
]
