"""Implementation of `pktlabctl stats ...` commands."""

from __future__ import annotations

import sys
from typing import TextIO

from pktlabctl.client import ControllerClient, ControllerClientError
from pktlabctl.output import render_stats, render_stats_reset


def run_stats_show(
    controller_url: str,
    *,
    json_output: bool,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Fetch and print datapath counters through the controller API."""

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        payload = ControllerClient(controller_url).get_datapath_stats()
    except ControllerClientError as exc:
        stderr.write(f"pktlabctl: {exc}\n")
        return 1

    stdout.write(render_stats(payload, json_output=json_output))
    stdout.write("\n")
    return 0


def run_stats_reset(
    controller_url: str,
    *,
    json_output: bool,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Reset datapath counters through the controller API and print the result."""

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        payload = ControllerClient(controller_url).reset_datapath_stats()
    except ControllerClientError as exc:
        stderr.write(f"pktlabctl: {exc}\n")
        return 1

    stdout.write(render_stats_reset(payload, json_output=json_output))
    stdout.write("\n")
    return 0


__all__ = ["run_stats_reset", "run_stats_show"]
