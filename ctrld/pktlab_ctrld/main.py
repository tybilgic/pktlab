"""Controller command-line entrypoint."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import uvicorn

from pktlab_ctrld.api.app import create_api_app
from pktlab_ctrld.app import ControllerConfig, ControllerRuntime

DEFAULT_CONTROLLER_HOST = "127.0.0.1"
DEFAULT_CONTROLLER_PORT = 8080
DEFAULT_DPDKD_BINARY = "build/dpdkd/pktlab-dpdkd"
DEFAULT_DPDKD_SOCKET_PATH = "/run/pktlab/dpdkd.sock"


def build_parser() -> argparse.ArgumentParser:
    """Construct the controller CLI parser."""

    parser = argparse.ArgumentParser(prog="pktlab-ctrld")
    parser.add_argument(
        "--host",
        default=os.getenv("PKTLAB_CTRLD_HOST", DEFAULT_CONTROLLER_HOST),
        help="HTTP listen address for the controller API",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PKTLAB_CTRLD_PORT", str(DEFAULT_CONTROLLER_PORT))),
        help="HTTP listen port for the controller API",
    )
    parser.add_argument(
        "--dpdkd-bin",
        default=os.getenv("PKTLAB_DPDKD_BIN", DEFAULT_DPDKD_BINARY),
        help="Path to the pktlab-dpdkd executable",
    )
    parser.add_argument(
        "--dpdkd-socket-path",
        default=os.getenv("PKTLAB_DPDKD_SOCKET_PATH", DEFAULT_DPDKD_SOCKET_PATH),
        help="Unix socket path used by pktlab-dpdkd",
    )
    parser.add_argument(
        "--startup-timeout-seconds",
        type=float,
        default=float(os.getenv("PKTLAB_DPDKD_STARTUP_TIMEOUT", "5.0")),
        help="Maximum time to wait for datapath IPC readiness",
    )
    parser.add_argument(
        "--no-supervise-datapath",
        action="store_true",
        help="Start the controller without launching pktlab-dpdkd",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("PKTLAB_CTRLD_LOG_LEVEL", "warning"),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the controller API service."""

    args = build_parser().parse_args(argv)
    config = ControllerConfig(
        datapath_binary=args.dpdkd_bin,
        datapath_socket_path=args.dpdkd_socket_path,
        datapath_startup_timeout_seconds=args.startup_timeout_seconds,
        supervise_datapath=not args.no_supervise_datapath,
    )
    controller = ControllerRuntime(config)
    app = create_api_app(controller)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
