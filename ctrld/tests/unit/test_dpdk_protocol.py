"""Unit tests for datapath protocol framing helpers."""

from __future__ import annotations

import json
import socket
import struct
import unittest

IMPORT_ERROR: ModuleNotFoundError | None = None

try:
    from pktlab_ctrld.dpdk_client import protocol
    from pktlab_ctrld.dpdk_client.models import GetHealthRequest, PingRequest, RawErrorEnvelope
    from pktlab_ctrld.error import DatapathProtocolError
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    if exc.name != "pydantic":
        raise
    IMPORT_ERROR = exc


@unittest.skipIf(IMPORT_ERROR is not None, "pydantic is not installed")
class DatapathProtocolTests(unittest.TestCase):
    """Exercise framing and basic envelope parsing without a real daemon."""

    def test_send_request_uses_big_endian_length_prefix(self) -> None:
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)

        request = PingRequest(id="req-unit-1")
        protocol.send_request(left, request)

        header = right.recv(4)
        payload_length = struct.unpack(">I", header)[0]
        self.assertGreater(payload_length, 0)

        payload = right.recv(payload_length)
        self.assertEqual(
            json.loads(payload.decode("utf-8")),
            {"id": "req-unit-1", "cmd": "ping", "payload": {}},
        )

    def test_recv_response_parses_success_envelope(self) -> None:
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)

        payload = json.dumps(
            {
                "id": "req-unit-2",
                "ok": True,
                "payload": {
                    "health": {
                        "state": "running",
                        "message": "ready",
                        "applied_rule_version": 0,
                        "ports_ready": False,
                        "paused": False,
                    }
                },
            }
        ).encode("utf-8")
        right.sendall(struct.pack(">I", len(payload)) + payload)

        response = protocol.recv_response(left)
        self.assertEqual(response.id, "req-unit-2")
        self.assertTrue(response.ok)
        self.assertEqual(response.payload["health"]["state"], "running")

    def test_recv_response_parses_error_envelope(self) -> None:
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)

        payload = json.dumps(
            {
                "id": "req-unit-3",
                "ok": False,
                "error": {"code": "UNKNOWN_COMMAND", "message": "unknown IPC command"},
            }
        ).encode("utf-8")
        right.sendall(struct.pack(">I", len(payload)) + payload)

        response = protocol.recv_response(left)
        self.assertIsInstance(response, RawErrorEnvelope)
        self.assertEqual(response.error.code.value, "UNKNOWN_COMMAND")

    def test_recv_response_rejects_invalid_shape(self) -> None:
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)

        payload = json.dumps({"id": "req-unit-4", "payload": {}}).encode("utf-8")
        right.sendall(struct.pack(">I", len(payload)) + payload)

        with self.assertRaises(DatapathProtocolError):
            protocol.recv_response(left)

    def test_encode_request_stays_within_frame_limit_for_supported_command(self) -> None:
        request = GetHealthRequest(id="req-unit-5")
        encoded = protocol.encode_request(request)
        self.assertLess(len(encoded) - protocol.FRAME_HEADER_STRUCT.size, protocol.MAX_FRAME_PAYLOAD_SIZE)


if __name__ == "__main__":
    unittest.main()
