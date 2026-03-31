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


if __name__ == "__main__":
    unittest.main()
