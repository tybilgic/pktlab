"""Implementation of `pktlabctl topology ...` commands."""

from __future__ import annotations

import sys
from typing import TextIO

from pktlabctl.client import ControllerClient, ControllerClientError
from pktlabctl.output import render_topology_result


def run_topology_apply(
    controller_url: str,
    *,
    config_path: str,
    json_output: bool,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Apply a topology through the controller API."""

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        payload = ControllerClient(controller_url).apply_topology(config_path)
    except (ControllerClientError, ValueError) as exc:
        stderr.write(f"pktlabctl: {exc}\n")
        return 1

    stdout.write(render_topology_result(payload, json_output=json_output))
    stdout.write("\n")
    return 0


def run_topology_destroy(
    controller_url: str,
    *,
    json_output: bool,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Destroy the active topology through the controller API."""

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        payload = ControllerClient(controller_url).destroy_topology()
    except ControllerClientError as exc:
        stderr.write(f"pktlabctl: {exc}\n")
        return 1

    stdout.write(render_topology_result(payload, json_output=json_output))
    stdout.write("\n")
    return 0


__all__ = ["run_topology_apply", "run_topology_destroy"]
