"""Small timing helpers for controller orchestration."""

from __future__ import annotations

import time
from collections.abc import Callable

from pktlab_ctrld.error import ErrorCode, PktlabError


def wait_until(
    predicate: Callable[[], bool],
    *,
    description: str,
    timeout_seconds: float,
    interval_seconds: float = 0.05,
) -> None:
    """Wait for a predicate to become true or raise a typed timeout error."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than zero")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval_seconds)

    raise PktlabError(
        ErrorCode.TIMEOUT,
        f"timed out waiting for {description}",
        context={
            "description": description,
            "timeout_seconds": timeout_seconds,
            "interval_seconds": interval_seconds,
        },
    )


__all__ = ["wait_until"]
