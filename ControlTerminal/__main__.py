"""Entry point: ``python -m ControlTerminal <animation_dir> [--port ... --speed ... --timeout ...]``."""

import argparse
import sys
from typing import List, Optional

from ControlTower.Presenter import add_connection_arguments, create_presenter
from ControlTower.common import SerialConfigLoadFailed

from .ControlTerminal import ControlTerminal


def build_parser() -> argparse.ArgumentParser:
    """Command-line parser: the shared connection arguments plus ``--refresh``."""
    parser = argparse.ArgumentParser(
        prog="python -m ControlTerminal",
        description="Terminal UI for controlling a drone swarm.",
    )
    add_connection_arguments(parser)
    parser.add_argument("--refresh", type=float, default=0.25, help="seconds between screen refreshes (default: 0.25)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Start the TUI.

    Args:
        argv: Command-line arguments; None means ``sys.argv[1:]``.

    Returns:
        Process exit code: 0 after a normal exit, 2 if the animation directory or the serial
        connection can't be set up (a one-line message goes to stderr).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.refresh <= 0:
        parser.error("--refresh must be greater than 0")

    try:
        tower, presenter, log_buffer = create_presenter(args)
    except (OSError, SerialConfigLoadFailed) as error:
        print(f"ControlTerminal: {error}", file=sys.stderr)
        return 2

    try:
        ControlTerminal(presenter, log_buffer, refresh_interval=args.refresh, shutdown=tower.shutdown).run()
    finally:
        log_buffer.uninstall()
    return 0


if __name__ == "__main__":
    sys.exit(main())
