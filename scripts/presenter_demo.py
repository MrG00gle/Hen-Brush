"""Live-updating terminal table driven only by the presenter layer (bounded, about 2 seconds).

Run from the repository root:
    .venv\\Scripts\\python.exe scripts/presenter_demo.py
"""

import argparse
import csv
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ControlTower.Presenter import DroneRow, add_connection_arguments, create_presenter  # noqa: E402

DRONES = 3
FRAMES = 12
FRAME_MS = 200
SNAPSHOTS = 5
SNAPSHOT_INTERVAL_S = 0.4
COLUMNS = (("ID", 4), ("Status", 8), ("Animation", 10), ("Position", 22), ("Error", 7), ("Step", 7))


def write_animation(directory: Path) -> None:
    """Write ``drone_<n>.csv`` files (``ts,x,y,z,r,g,b``) in which every drone flies a straight line."""
    for drone in range(DRONES):
        with (directory / f"drone_{drone}.csv").open("w", newline="") as file:
            writer = csv.writer(file)
            for frame in range(FRAMES):
                writer.writerow([frame * FRAME_MS, frame + drone * 10, drone, 1.5, 255, 0, 0])


def format_table(rows: Iterable[DroneRow]) -> str:
    """Render presenter rows as a fixed-width text table.

    Args:
        rows: Rows produced by ``DronePresenter.rows()``.

    Returns:
        The table as a multi-line string.
    """
    header = "  ".join(title.ljust(width) for title, width in COLUMNS)
    lines = [header, "  ".join("-" * width for _, width in COLUMNS)]
    for row in rows:
        values = (row.drone_id, row.status, row.animation_status, row.position, row.position_error, row.step_text)
        lines.append("  ".join(str(value).ljust(width) for value, (_, width) in zip(values, COLUMNS)))
    return "\n".join(lines)


def main() -> int:
    """Run the demo against a temporary animation over ``loop://``.

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_connection_arguments(parser)
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        write_animation(directory)
        args = parser.parse_args([str(directory), "--port", "loop://", "--speed", "115200", "--timeout", "0.2"])
        tower, presenter, log_buffer = create_presenter(args)
        try:
            print(presenter.start_all().message)
            for snapshot in range(1, SNAPSHOTS + 1):
                print(f"\nSnapshot {snapshot}/{SNAPSHOTS}")
                print(format_table(presenter.rows()))
                time.sleep(SNAPSHOT_INTERVAL_S)
            print(presenter.stop_all().message)
            print("\nFinal")
            print(format_table(presenter.rows()))
            print("\nLog")
            for entry in log_buffer.entries()[-5:]:
                print(f"{entry.level:<7} {entry.message}")
        finally:
            log_buffer.uninstall()
            tower.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
