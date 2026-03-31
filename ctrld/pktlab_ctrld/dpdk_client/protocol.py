"""Framing helpers for controller-to-datapath Unix socket IPC."""

from __future__ import annotations

import json
import socket
import struct
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from pktlab_ctrld.error import DatapathProtocolError

from .models import RawErrorEnvelope, RawSuccessEnvelope, RequestEnvelope, ResponseEnvelope

FRAME_HEADER_STRUCT = struct.Struct(">I")
MAX_FRAME_PAYLOAD_SIZE = 16_384


def encode_request(request: RequestEnvelope) -> bytes:
    """Serialize a typed request into a length-prefixed frame."""

    payload = request.model_dump_json().encode("utf-8")
    return _frame_payload(payload)


def send_request(sock: socket.socket, request: RequestEnvelope) -> None:
    """Send a typed request over an already-connected Unix socket."""

    sock.sendall(encode_request(request))


def recv_response(sock: socket.socket) -> ResponseEnvelope:
    """Receive and validate a basic datapath response envelope."""

    response_bytes = recv_frame(sock)
    return parse_response(response_bytes)


def recv_frame(sock: socket.socket) -> bytes:
    """Read one length-prefixed frame from the socket."""

    header = _read_exact(sock, FRAME_HEADER_STRUCT.size)
    (payload_length,) = FRAME_HEADER_STRUCT.unpack(header)
    if payload_length == 0 or payload_length >= MAX_FRAME_PAYLOAD_SIZE:
        raise DatapathProtocolError(
            "received an invalid IPC frame length",
            context={"payload_length": payload_length, "max_payload_length": MAX_FRAME_PAYLOAD_SIZE - 1},
        )
    return _read_exact(sock, payload_length)


def parse_response(frame_payload: bytes) -> ResponseEnvelope:
    """Parse JSON bytes and validate the basic response envelope shape."""

    try:
        raw = json.loads(frame_payload.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise DatapathProtocolError("IPC response is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise DatapathProtocolError(
            "IPC response is not valid JSON",
            context={"line": exc.lineno, "column": exc.colno, "position": exc.pos},
        ) from exc

    if not isinstance(raw, dict):
        raise DatapathProtocolError(
            "IPC response must be a JSON object",
            context={"response_type": type(raw).__name__},
        )

    try:
        if raw.get("ok") is True:
            return RawSuccessEnvelope.model_validate(raw)
        if raw.get("ok") is False:
            return RawErrorEnvelope.model_validate(raw)
    except PydanticValidationError as exc:
        raise DatapathProtocolError(
            "IPC response failed basic envelope validation",
            context={"errors": exc.errors(include_url=False)},
        ) from exc

    raise DatapathProtocolError(
        "IPC response did not contain a valid ok discriminator",
        context={"keys": sorted(raw.keys())},
    )


def _frame_payload(payload: bytes) -> bytes:
    """Apply the shared big-endian frame header to a JSON payload."""

    payload_length = len(payload)
    if payload_length == 0 or payload_length >= MAX_FRAME_PAYLOAD_SIZE:
        raise DatapathProtocolError(
            "request payload exceeds the supported IPC frame size",
            context={"payload_length": payload_length, "max_payload_length": MAX_FRAME_PAYLOAD_SIZE - 1},
        )

    return FRAME_HEADER_STRUCT.pack(payload_length) + payload


def _read_exact(sock: socket.socket, size: int) -> bytes:
    """Read exactly ``size`` bytes or raise a protocol error on EOF."""

    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise DatapathProtocolError(
                "unexpected EOF while reading an IPC frame",
                context={"expected_bytes": size, "remaining_bytes": remaining},
            )
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


__all__ = [
    "FRAME_HEADER_STRUCT",
    "MAX_FRAME_PAYLOAD_SIZE",
    "encode_request",
    "parse_response",
    "recv_frame",
    "recv_response",
    "send_request",
]
