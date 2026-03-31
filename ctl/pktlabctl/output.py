"""Render controller status output for human and JSON modes."""

from __future__ import annotations

import json

from .client import HealthResponseModel


def render_status(payload: HealthResponseModel, *, json_output: bool) -> str:
    """Render a status payload for CLI output."""

    if json_output:
        return json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True)
    return render_human_status(payload)


def render_human_status(payload: HealthResponseModel) -> str:
    """Format a health payload as a readable multi-line status report."""

    controller = payload.controller
    datapath = payload.datapath

    lines = [
        f"controller: {controller.state} ({controller.message})",
        f"  service: {controller.service} {controller.version}",
        f"datapath: {'reachable' if datapath.reachable else 'unreachable'}",
        f"  managed: {'yes' if datapath.managed else 'no'}",
        f"  socket: {datapath.socket_path}",
        f"  pid: {datapath.pid if datapath.pid is not None else 'n/a'}",
    ]

    if datapath.state is not None:
        lines.append(f"  state: {datapath.state}")
    if datapath.message:
        lines.append(f"  message: {datapath.message}")
    if datapath.service and datapath.version:
        service_line = f"  service: {datapath.service} {datapath.version}"
        if datapath.dpdk_version:
            service_line += f" (DPDK {datapath.dpdk_version})"
        lines.append(service_line)
    if datapath.applied_rule_version is not None:
        lines.append(f"  applied_rule_version: {datapath.applied_rule_version}")
    lines.append(f"  ports_ready: {'yes' if datapath.ports_ready else 'no'}")
    lines.append(f"  paused: {'yes' if datapath.paused else 'no'}")
    if datapath.exit_code is not None:
        lines.append(f"  exit_code: {datapath.exit_code}")
    if datapath.last_error:
        lines.append(f"  error: {datapath.last_error}")

    return "\n".join(lines)


__all__ = ["render_human_status", "render_status"]
