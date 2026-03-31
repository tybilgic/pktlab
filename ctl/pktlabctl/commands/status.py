"""Implementation of `pktlabctl status`."""

from __future__ import annotations

import sys
from typing import TextIO

from pktlabctl.client import ControllerClient, ControllerClientError
from pktlabctl.output import render_status


def run_status(
    controller_url: str,
    *,
    json_output: bool,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Fetch and print controller status."""

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        payload = ControllerClient(controller_url).get_health()
    except ControllerClientError as exc:
        stderr.write(f"pktlabctl: {exc}\n")
        return 1

    stdout.write(render_status(payload, json_output=json_output))
    stdout.write("\n")
    return 0


__all__ = ["run_status"]
