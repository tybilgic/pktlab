"""Concrete Unix-socket client for talking to pktlab-dpdkd."""

from __future__ import annotations

import socket
import uuid
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from pktlab_ctrld.error import DatapathProtocolError, DatapathTransportError

from . import protocol
from .models import (
    AckPayload,
    CommandResult,
    GetPortsRequest,
    GetStatsRequest,
    GetHealthRequest,
    GetVersionRequest,
    PortsPayload,
    StatsPayload,
    HealthPayload,
    PingRequest,
    RawErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
    VersionPayload,
)

PayloadT = TypeVar("PayloadT", bound=BaseModel)


class DpdkClient:
    """Small typed client for the datapath daemon IPC socket."""

    def __init__(
        self,
        socket_path: str,
        *,
        timeout_seconds: float = 1.0,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not socket_path:
            raise ValueError("socket_path must be a non-empty string")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self.socket_path = socket_path
        self.timeout_seconds = timeout_seconds
        self._request_id_factory = request_id_factory or _default_request_id

    def ping(self) -> CommandResult[AckPayload]:
        """Send a ping request to the datapath daemon."""

        request = PingRequest(id=self._request_id_factory())
        return self._typed_call(request, AckPayload)

    def get_version(self) -> CommandResult[VersionPayload]:
        """Fetch the datapath daemon version metadata."""

        request = GetVersionRequest(id=self._request_id_factory())
        return self._typed_call(request, VersionPayload)

    def get_health(self) -> CommandResult[HealthPayload]:
        """Fetch the current datapath health snapshot."""

        request = GetHealthRequest(id=self._request_id_factory())
        return self._typed_call(request, HealthPayload)

    def get_ports(self) -> CommandResult[PortsPayload]:
        """Fetch the current datapath port status."""

        request = GetPortsRequest(id=self._request_id_factory())
        return self._typed_call(request, PortsPayload)

    def get_stats(self) -> CommandResult[StatsPayload]:
        """Fetch the current datapath counters."""

        request = GetStatsRequest(id=self._request_id_factory())
        return self._typed_call(request, StatsPayload)

    def _typed_call(
        self,
        request: RequestEnvelope,
        payload_type: type[PayloadT],
    ) -> CommandResult[PayloadT]:
        """Execute one request and return a typed success or daemon error result."""

        response = self._exchange(request)
        if response.id != request.id:
            raise DatapathProtocolError(
                "IPC response id did not match the request id",
                context={"request_id": request.id, "response_id": response.id, "cmd": request.cmd},
            )

        if isinstance(response, RawErrorEnvelope):
            return CommandResult.failure(request.id, response.error)

        try:
            payload = payload_type.model_validate(response.payload)
        except PydanticValidationError as exc:
            raise DatapathProtocolError(
                "IPC success payload failed validation",
                context={
                    "request_id": request.id,
                    "cmd": request.cmd,
                    "errors": exc.errors(include_url=False),
                },
            ) from exc

        return CommandResult.success(request.id, payload)

    def _exchange(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Perform one request/response round-trip over the Unix socket."""

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(self.timeout_seconds)
                client.connect(self.socket_path)
                protocol.send_request(client, request)
                return protocol.recv_response(client)
        except FileNotFoundError as exc:
            raise DatapathTransportError(
                "datapath IPC socket was not found",
                context={"socket_path": self.socket_path, "cmd": request.cmd},
            ) from exc
        except ConnectionRefusedError as exc:
            raise DatapathTransportError(
                "datapath IPC socket refused the connection",
                context={"socket_path": self.socket_path, "cmd": request.cmd},
            ) from exc
        except socket.timeout as exc:
            raise DatapathTransportError(
                "datapath IPC request timed out",
                context={
                    "socket_path": self.socket_path,
                    "cmd": request.cmd,
                    "timeout_seconds": self.timeout_seconds,
                },
            ) from exc
        except OSError as exc:
            raise DatapathTransportError(
                "datapath IPC transport failed",
                context={
                    "socket_path": self.socket_path,
                    "cmd": request.cmd,
                    "errno": getattr(exc, "errno", None),
                },
            ) from exc


def _default_request_id() -> str:
    """Generate a request id that satisfies the shared schema pattern."""

    return f"req-{uuid.uuid4().hex[:12]}"


__all__ = ["DpdkClient"]
