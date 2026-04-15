"""Unit tests for the typed datapath client result mapping."""

from __future__ import annotations

import unittest
from unittest import mock

IMPORT_ERROR: ModuleNotFoundError | None = None

try:
    from pktlab_ctrld.dpdk_client.client import DpdkClient
    from pktlab_ctrld.dpdk_client.models import (
        DatapathErrorCode,
        DatapathErrorModel,
        RawErrorEnvelope,
        RawSuccessEnvelope,
    )
    from pktlab_ctrld.error import DatapathProtocolError
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    if exc.name != "pydantic":
        raise
    IMPORT_ERROR = exc


@unittest.skipIf(IMPORT_ERROR is not None, "pydantic is not installed")
class DpdkClientUnitTests(unittest.TestCase):
    """Check typed payload/error handling separately from the transport path."""

    def test_ping_returns_typed_success_result(self) -> None:
        client = DpdkClient("/tmp/pktlab.sock", request_id_factory=lambda: "req-client-1")

        with mock.patch.object(
            client,
            "_exchange",
            return_value=RawSuccessEnvelope(
                id="req-client-1",
                ok=True,
                payload={"message": "pong"},
            ),
        ):
            result = client.ping()

        self.assertTrue(result.ok)
        self.assertEqual(result.unwrap().message, "pong")

    def test_ping_returns_typed_error_result(self) -> None:
        client = DpdkClient("/tmp/pktlab.sock", request_id_factory=lambda: "req-client-2")

        with mock.patch.object(
            client,
            "_exchange",
            return_value=RawErrorEnvelope(
                id="req-client-2",
                ok=False,
                error=DatapathErrorModel(
                    code=DatapathErrorCode.UNKNOWN_COMMAND,
                    message="unknown IPC command",
                ),
            ),
        ):
            result = client.ping()

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, DatapathErrorCode.UNKNOWN_COMMAND)

    def test_ping_rejects_success_payload_shape_mismatch(self) -> None:
        client = DpdkClient("/tmp/pktlab.sock", request_id_factory=lambda: "req-client-3")

        with mock.patch.object(
            client,
            "_exchange",
            return_value=RawSuccessEnvelope(
                id="req-client-3",
                ok=True,
                payload={"unexpected": "field"},
            ),
        ):
            with self.assertRaises(DatapathProtocolError):
                client.ping()

    def test_get_ports_returns_typed_success_result(self) -> None:
        client = DpdkClient("/tmp/pktlab.sock", request_id_factory=lambda: "req-client-4")

        with mock.patch.object(
            client,
            "_exchange",
            return_value=RawSuccessEnvelope(
                id="req-client-4",
                ok=True,
                payload={
                    "ports": [
                        {"name": "dtap0", "port_id": 0, "role": "ingress", "state": "down"},
                        {"name": "dtap1", "port_id": 1, "role": "egress", "state": "down"},
                    ]
                },
            ),
        ):
            result = client.get_ports()

        self.assertTrue(result.ok)
        self.assertEqual([port.name for port in result.unwrap().ports], ["dtap0", "dtap1"])

    def test_get_stats_returns_typed_success_result(self) -> None:
        client = DpdkClient("/tmp/pktlab.sock", request_id_factory=lambda: "req-client-5")

        with mock.patch.object(
            client,
            "_exchange",
            return_value=RawSuccessEnvelope(
                id="req-client-5",
                ok=True,
                payload={
                    "stats": {
                        "rx_packets": 1,
                        "tx_packets": 1,
                        "drop_packets": 0,
                        "drop_parse_errors": 0,
                        "drop_no_match": 0,
                        "rx_bursts": 1,
                        "tx_bursts": 1,
                        "unsent_packets": 0,
                        "rule_hits": {},
                    }
                },
            ),
        ):
            result = client.get_stats()

        self.assertTrue(result.ok)
        self.assertEqual(result.unwrap().stats.rx_packets, 1)

    def test_reset_stats_returns_typed_success_result(self) -> None:
        client = DpdkClient("/tmp/pktlab.sock", request_id_factory=lambda: "req-client-6")

        with mock.patch.object(
            client,
            "_exchange",
            return_value=RawSuccessEnvelope(
                id="req-client-6",
                ok=True,
                payload={"message": "datapath counters reset"},
            ),
        ):
            result = client.reset_stats()

        self.assertTrue(result.ok)
        self.assertEqual(result.unwrap().message, "datapath counters reset")


if __name__ == "__main__":
    unittest.main()
