"""Argument parsing and command dispatch for pktlabctl."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch the CLI entrypoint."""

    args = build_parser().parse_args(argv)
    if args.command == "status":
        return run_status(args.controller_url, json_output=args.json_output)

    raise SystemExit(f"unsupported command: {args.command}")


__all__ = ["build_parser", "main"]
