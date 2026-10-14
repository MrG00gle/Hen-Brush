"""Command-line arguments and presenter construction shared by the TUI and the GUI entry points."""
import argparse
from typing import Tuple

from ..ControlTower import ControlTower
from .DronePresenter import DronePresenter
from .LogBuffer import LogBuffer


def add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the command-line arguments shared by the TUI and the GUI.

    Args:
        parser: Parser to extend with ``animation_dir``, ``--port``, ``--speed`` and ``--timeout``.
    """
    parser.add_argument("animation_dir", help="directory with the drone CSV files and an optional JSON serial config")
    parser.add_argument("--port", help="serial port or pyserial URL (e.g. COM3, /dev/ttyUSB0, loop://)")
    parser.add_argument("--speed", type=int, help="serial speed in baud")
    parser.add_argument("--timeout", type=float, help="serial read timeout in seconds")


def create_presenter(args: argparse.Namespace) -> Tuple[ControlTower, DronePresenter, LogBuffer]:
    """Build the ControlTower from parsed arguments and wire the presenter and log buffer to it.

    The log buffer is installed on the root logger; the caller removes it with
    ``log_buffer.uninstall()`` and shuts the tower down with ``tower.shutdown()``.

    Args:
        args: Namespace produced by a parser extended with ``add_connection_arguments``.

    Returns:
        ``(tower, presenter, log_buffer)``.

    Raises:
        FileNotFoundError: If the animation directory does not exist.
        NotADirectoryError: If the animation path is not a directory.
        SerialConfigLoadFailed: If neither the arguments nor the animation directory give a complete serial config.
    """
    tower = ControlTower(args.animation_dir, args.port, args.speed, args.timeout)
    log_buffer = LogBuffer()
    log_buffer.install()
    return tower, DronePresenter(tower), log_buffer
