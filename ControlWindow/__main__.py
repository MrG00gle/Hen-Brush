"""Entry point: ``python -m ControlWindow <animation_dir> [--port ... --speed ... --timeout ...]``."""

import argparse
import sys
from typing import Callable, List, Optional

from ControlTower.Presenter import add_connection_arguments, create_presenter
from ControlTower.common import SerialConfigLoadFailed


def build_parser() -> argparse.ArgumentParser:
    """Command-line parser with the connection arguments shared with the terminal UI."""
    parser = argparse.ArgumentParser(
        prog="python -m ControlWindow",
        description="GTK4 window for controlling a drone swarm.",
    )
    add_connection_arguments(parser)
    return parser


def _load_application() -> Callable[..., object]:
    """Import the GTK application class; kept apart so this module imports without PyGObject."""
    from .app import HenBrushApplication
    return HenBrushApplication


def main(argv: Optional[List[str]] = None) -> int:
    """Start the GUI.

    Args:
        argv: Command-line arguments; None means ``sys.argv[1:]``.

    Returns:
        Process exit code: the application's exit status after a normal run; 2 if the animation
        directory or the serial connection can't be set up; 1 if GTK4, libadwaita or
        blueprint-compiler are not available. A one-line message goes to stderr for the last two.
    """
    args = build_parser().parse_args(argv)

    # Load GTK first so a missing GTK does not open the serial port for nothing.
    try:
        application_class = _load_application()
    except (ImportError, ValueError, RuntimeError) as error:
        print(f"ControlWindow: GTK4/libadwaita GUI is not available: {error}", file=sys.stderr)
        return 1

    try:
        tower, presenter, log_buffer = create_presenter(args)
    except (OSError, SerialConfigLoadFailed) as error:
        print(f"ControlWindow: {error}", file=sys.stderr)
        return 2

    try:
        # Empty argv: GTK must not parse our own command-line options.
        return application_class(presenter, log_buffer, shutdown=tower.shutdown).run([])
    finally:
        tower.shutdown()
        log_buffer.uninstall()


if __name__ == "__main__":
    sys.exit(main())
