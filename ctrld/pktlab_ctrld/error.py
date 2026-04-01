"""Shared error types for controller-side code."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Project-level typed error codes."""

    DATAPATH_TRANSPORT_ERROR = "DATAPATH_TRANSPORT_ERROR"
    CONFIG_PARSE_ERROR = "CONFIG_PARSE_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    UNKNOWN_COMMAND = "UNKNOWN_COMMAND"
    RULE_VALIDATION_ERROR = "RULE_VALIDATION_ERROR"
    TOPOLOGY_VALIDATION_ERROR = "TOPOLOGY_VALIDATION_ERROR"
    TOPOLOGY_APPLY_ERROR = "TOPOLOGY_APPLY_ERROR"
    PROCESS_ERROR = "PROCESS_ERROR"
    PORT_INIT_ERROR = "PORT_INIT_ERROR"
    STATE_CONFLICT = "STATE_CONFLICT"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class PktlabError(Exception):
    """Base typed error for controller-side code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert the error to a serializable structure."""

        payload: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.context:
            payload["context"] = self.context
        return payload


class ValidationError(PktlabError):
    """Typed validation failure."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.TOPOLOGY_VALIDATION_ERROR,
        issues: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        merged_context = dict(context or {})
        if issues:
            merged_context["issues"] = issues
        super().__init__(
            code,
            message,
            context=merged_context or None,
        )
        self.issues = tuple(merged_context.get("issues", ()))


class ConfigParseError(PktlabError):
    """Typed configuration parse failure."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            ErrorCode.CONFIG_PARSE_ERROR,
            message,
            context=context,
        )


class DatapathProtocolError(PktlabError):
    """Typed datapath protocol failure."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            ErrorCode.INVALID_PAYLOAD,
            message,
            context=context,
        )


class DatapathTransportError(PktlabError):
    """Typed transport failure while talking to the datapath socket."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            ErrorCode.DATAPATH_TRANSPORT_ERROR,
            message,
            context=context,
        )


class ProcessExecutionError(PktlabError):
    """Typed external process failure."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            ErrorCode.PROCESS_ERROR,
            message,
            context=context,
        )


__all__ = [
    "DatapathProtocolError",
    "DatapathTransportError",
    "ErrorCode",
    "ConfigParseError",
    "PktlabError",
    "ProcessExecutionError",
    "ValidationError",
]
