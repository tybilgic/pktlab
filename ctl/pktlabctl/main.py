"""CLI entrypoint for pktlabctl."""

from __future__ import annotations

from collections.abc import Sequence

from pktlabctl.cli import main as cli_main


def main(argv: Sequence[str] | None = None) -> int:
    """Run the pktlab CLI."""

    return cli_main(argv)


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
