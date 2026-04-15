"""Render controller status and topology output for human and JSON modes."""

from __future__ import annotations

import json

from .client import DatapathStatsResponseModel, DatapathStatusResponseModel, TopologyOperationResponseModel


def render_status(payload: DatapathStatusResponseModel, *, json_output: bool) -> str:
    """Render a datapath status payload for CLI output."""

    if json_output:
        return json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True)
    return render_human_status(payload)


def render_human_status(payload: DatapathStatusResponseModel) -> str:
    """Format a datapath status payload as a readable multi-line status report."""

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
    if payload.ports:
        lines.append("ports:")
        for port in payload.ports:
            lines.append(
                f"  {port.role}: {port.name} (id={port.port_id}, state={port.state})"
            )

    return "\n".join(lines)


def render_stats(payload: DatapathStatsResponseModel, *, json_output: bool) -> str:
    """Render a datapath stats payload for CLI output."""

    if json_output:
        return json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True)
    return render_human_stats(payload)


def render_human_stats(payload: DatapathStatsResponseModel) -> str:
    """Format datapath counters as a readable multi-line report."""

    datapath = payload.datapath
    stats = payload.stats

    lines = [
        f"datapath stats: {datapath.state if datapath.state is not None else 'unknown'}",
        f"  socket: {datapath.socket_path}",
        f"  rx_packets: {stats.rx_packets}",
        f"  tx_packets: {stats.tx_packets}",
        f"  drop_packets: {stats.drop_packets}",
        f"  drop_parse_errors: {stats.drop_parse_errors}",
        f"  drop_no_match: {stats.drop_no_match}",
        f"  rx_bursts: {stats.rx_bursts}",
        f"  tx_bursts: {stats.tx_bursts}",
        f"  unsent_packets: {stats.unsent_packets}",
    ]
    if stats.rule_hits:
        lines.append("  rule_hits:")
        for rule_id in sorted(stats.rule_hits, key=int):
            lines.append(f"    {rule_id}: {stats.rule_hits[rule_id]}")
    else:
        lines.append("  rule_hits: none")
    return "\n".join(lines)


def render_topology_result(payload: TopologyOperationResponseModel, *, json_output: bool) -> str:
    """Render a topology lifecycle result for CLI output."""

    if json_output:
        return json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True)

    lines = [
        f"topology {payload.operation}: {payload.message}",
        f"  applied: {'yes' if payload.applied else 'no'}",
        f"  datapath_running: {'yes' if payload.datapath_running else 'no'}",
    ]
    if payload.topology_name is not None:
        lines.append(f"  topology: {payload.topology_name}")
    if payload.config_path is not None:
        lines.append(f"  config_path: {payload.config_path}")
    if payload.datapath_namespace is not None:
        lines.append(f"  datapath_namespace: {payload.datapath_namespace}")
    return "\n".join(lines)


__all__ = [
    "render_human_stats",
    "render_human_status",
    "render_stats",
    "render_status",
    "render_topology_result",
]
