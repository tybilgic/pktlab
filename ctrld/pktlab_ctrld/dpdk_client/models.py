"""Typed IPC models for controller-to-datapath communication."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

REQUEST_ID_PATTERN = r"^[A-Za-z0-9._:-]+$"

DatapathCommand = Literal[
    "ping",
    "get_version",
    "get_health",
    "get_ports",
    "get_stats",
    "reset_stats",
    "get_rules",
    "replace_rules",
    "pause_datapath",
    "resume_datapath",
    "shutdown",
]

DatapathStateValue = Literal[
    "starting",
    "running",
    "paused",
    "degraded",
    "stopping",
    "failed",
]


class DatapathErrorCode(StrEnum):
    """Error codes returned by the datapath IPC server."""

    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    UNKNOWN_COMMAND = "UNKNOWN_COMMAND"
    RULE_VALIDATION_ERROR = "RULE_VALIDATION_ERROR"
    PORT_INIT_ERROR = "PORT_INIT_ERROR"
    STATE_CONFLICT = "STATE_CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class EmptyPayload(BaseModel):
    """Empty payload used by request/response messages without command data."""

    model_config = ConfigDict(extra="forbid")


class PingRequest(BaseModel):
    """Typed request envelope for the ping command."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=REQUEST_ID_PATTERN)
    cmd: Literal["ping"] = "ping"
    payload: EmptyPayload = Field(default_factory=EmptyPayload)


class GetVersionRequest(BaseModel):
    """Typed request envelope for the get_version command."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=REQUEST_ID_PATTERN)
    cmd: Literal["get_version"] = "get_version"
    payload: EmptyPayload = Field(default_factory=EmptyPayload)


class GetHealthRequest(BaseModel):
    """Typed request envelope for the get_health command."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=REQUEST_ID_PATTERN)
    cmd: Literal["get_health"] = "get_health"
    payload: EmptyPayload = Field(default_factory=EmptyPayload)


RequestEnvelope = PingRequest | GetVersionRequest | GetHealthRequest


class DatapathErrorModel(BaseModel):
    """Daemon-reported error payload."""

    model_config = ConfigDict(extra="forbid")

    code: DatapathErrorCode
    message: str = Field(min_length=1)


class RawSuccessEnvelope(BaseModel):
    """Basic success envelope validation before payload-specific parsing."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=REQUEST_ID_PATTERN)
    ok: Literal[True] = True
    payload: dict[str, Any]


class RawErrorEnvelope(BaseModel):
    """Basic error envelope validation before the client maps the result."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=REQUEST_ID_PATTERN)
    ok: Literal[False] = False
    error: DatapathErrorModel


ResponseEnvelope = RawSuccessEnvelope | RawErrorEnvelope


class AckPayload(BaseModel):
    """Generic acknowledgement payload."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)


class VersionPayload(BaseModel):
    """Datapath version-report payload."""

    model_config = ConfigDict(extra="forbid")

    service: Literal["pktlab-dpdkd"]
    version: str = Field(min_length=1)
    dpdk_version: str = Field(min_length=1)


class HealthStateModel(BaseModel):
    """Current datapath health snapshot."""

    model_config = ConfigDict(extra="forbid")

    state: DatapathStateValue
    message: str
    applied_rule_version: int = Field(ge=0)
    ports_ready: bool
    paused: bool


class HealthPayload(BaseModel):
    """Top-level health response payload."""

    model_config = ConfigDict(extra="forbid")

    health: HealthStateModel


PayloadT = TypeVar("PayloadT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class CommandResult(Generic[PayloadT]):
    """Typed result for a datapath command."""

    request_id: str
    payload: PayloadT | None = None
    error: DatapathErrorModel | None = None

    @property
    def ok(self) -> bool:
        """Return whether the datapath accepted the command."""

        return self.error is None

    def unwrap(self) -> PayloadT:
        """Return the payload or raise if the command failed."""

        if self.payload is None:
            raise RuntimeError("cannot unwrap a failed command result")
        return self.payload

    @classmethod
    def success(cls, request_id: str, payload: PayloadT) -> "CommandResult[PayloadT]":
        """Construct a successful typed result."""

        return cls(request_id=request_id, payload=payload)

    @classmethod
    def failure(cls, request_id: str, error: DatapathErrorModel) -> "CommandResult[PayloadT]":
        """Construct a daemon-reported failure result."""

        return cls(request_id=request_id, error=error)


__all__ = [
    "AckPayload",
    "CommandResult",
    "DatapathCommand",
    "DatapathErrorCode",
    "DatapathErrorModel",
    "DatapathStateValue",
    "EmptyPayload",
    "GetHealthRequest",
    "GetVersionRequest",
    "HealthPayload",
    "HealthStateModel",
    "PingRequest",
    "REQUEST_ID_PATTERN",
    "RawErrorEnvelope",
    "RawSuccessEnvelope",
    "RequestEnvelope",
    "ResponseEnvelope",
    "VersionPayload",
]
