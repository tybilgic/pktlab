"""Implementation of `pktlabctl datapath ...` commands."""

from __future__ import annotations

import sys
from typing import TextIO

from pktlabctl.client import ControllerClient, ControllerClientError
from pktlabctl.output import render_datapath_control


def run_datapath_pause(
    controller_url: str,
    *,
    json_output: bool,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Pause datapath forwarding through the controller API."""

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        payload = ControllerClient(controller_url).pause_datapath()
    except ControllerClientError as exc:
        stderr.write(f"pktlabctl: {exc}\n")
        return 1

    stdout.write(render_datapath_control("pause", payload, json_output=json_output))
    stdout.write("\n")
    return 0


def run_datapath_resume(
    controller_url: str,
    *,
    json_output: bool,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Resume datapath forwarding through the controller API."""

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        payload = ControllerClient(controller_url).resume_datapath()
    except ControllerClientError as exc:
        stderr.write(f"pktlabctl: {exc}\n")
        return 1

    stdout.write(render_datapath_control("resume", payload, json_output=json_output))
    stdout.write("\n")
    return 0


__all__ = ["run_datapath_pause", "run_datapath_resume"]
