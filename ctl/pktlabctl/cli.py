"""Argument parsing and command dispatch for pktlabctl."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from pktlabctl.commands.datapath import run_datapath_pause, run_datapath_resume
from pktlabctl.commands.stats import run_stats_reset, run_stats_show
from pktlabctl.commands.topology import run_topology_apply, run_topology_destroy
from pktlabctl.commands.status import run_status

DEFAULT_CONTROLLER_URL = "http://127.0.0.1:8080"


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level CLI parser."""

    parser = argparse.ArgumentParser(prog="pktlabctl")
    parser.add_argument(
        "--controller-url",
        default=os.getenv("PKTLAB_CTRLD_URL", DEFAULT_CONTROLLER_URL),
        help="Base URL for pktlab-ctrld",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Render command output as JSON",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Show controller and datapath health")

    stats_parser = subparsers.add_parser("stats", help="Show datapath counters")
    stats_subparsers = stats_parser.add_subparsers(dest="stats_command", required=True)
    stats_subparsers.add_parser("show", help="Show current datapath counters")
    stats_subparsers.add_parser("reset", help="Reset datapath counters")

    datapath_parser = subparsers.add_parser("datapath", help="Control the datapath runtime")
    datapath_subparsers = datapath_parser.add_subparsers(dest="datapath_command", required=True)
    datapath_subparsers.add_parser("pause", help="Pause datapath forwarding")
    datapath_subparsers.add_parser("resume", help="Resume datapath forwarding")

    topology_parser = subparsers.add_parser("topology", help="Manage the lab topology")
    topology_subparsers = topology_parser.add_subparsers(dest="topology_command", required=True)
    topology_apply_parser = topology_subparsers.add_parser("apply", help="Apply a topology YAML file")
    topology_apply_parser.add_argument(
        "-f",
        "--file",
        dest="config_path",
        required=True,
        help="Path to the topology YAML file visible to pktlab-ctrld",
    )
    topology_subparsers.add_parser("destroy", help="Destroy the currently applied topology")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch the CLI entrypoint."""

    args = build_parser().parse_args(argv)
    if args.command == "status":
        return run_status(args.controller_url, json_output=args.json_output)
    if args.command == "stats":
        if args.stats_command == "show":
            return run_stats_show(args.controller_url, json_output=args.json_output)
        if args.stats_command == "reset":
            return run_stats_reset(args.controller_url, json_output=args.json_output)
    if args.command == "datapath":
        if args.datapath_command == "pause":
            return run_datapath_pause(args.controller_url, json_output=args.json_output)
        if args.datapath_command == "resume":
            return run_datapath_resume(args.controller_url, json_output=args.json_output)
    if args.command == "topology":
        if args.topology_command == "apply":
            return run_topology_apply(
                args.controller_url,
                config_path=args.config_path,
                json_output=args.json_output,
            )
        if args.topology_command == "destroy":
            return run_topology_destroy(args.controller_url, json_output=args.json_output)

    raise SystemExit(f"unsupported command: {args.command}")


__all__ = ["build_parser", "main"]
