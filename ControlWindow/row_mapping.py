"""GTK-free helpers between the presenter and the GTK widgets.

Keeping this logic free of ``gi`` lets it be tested anywhere. The GTK code only applies the results.
"""

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence, Tuple

from ControlTower.Presenter import DroneRow

# The same six columns, in the same order, as the terminal UI: (key, title).
COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("id", "ID"),
    ("status", "Drone Status"),
    ("animation_status", "Animation Status"),
    ("position", "Position"),
    ("position_error", "Pos. error"),
    ("step", "Animation Step"),
)
COLUMN_KEYS: Tuple[str, ...] = tuple(key for key, _ in COLUMNS)


@dataclass(frozen=True)
class RowDiff:
    """What changed between two snapshots of presenter rows.

    Attributes:
        added: Rows whose drone id was not in the previous snapshot, in input order.
        changed: Rows whose id was known but whose values differ, in input order.
        removed: Ids that were in the previous snapshot but are gone, ascending.
    """

    added: Tuple[DroneRow, ...]
    changed: Tuple[DroneRow, ...]
    removed: Tuple[int, ...]

    @property
    def is_empty(self) -> bool:
        """True if nothing was added, changed or removed."""
        return not (self.added or self.changed or self.removed)


def row_values(row: DroneRow) -> Dict[str, str]:
    """Cell text of a presenter row, keyed by ``COLUMNS`` key.

    Args:
        row: A row from ``DronePresenter.rows()``. Its strings are used as they are.

    Returns:
        One entry per column.
    """
    return {
        "id": str(row.drone_id),
        "status": row.status,
        "animation_status": row.animation_status,
        "position": row.position,
        "position_error": row.position_error,
        "step": row.step_text,
    }


def diff_rows(previous: Mapping[int, DroneRow], rows: Sequence[DroneRow]) -> RowDiff:
    """Compare the rows shown so far with fresh rows, so the UI only touches what changed.

    Args:
        previous: Rows currently shown, by drone id.
        rows: Fresh rows from the presenter.

    Returns:
        The added, changed and removed rows. Unchanged rows appear nowhere.
    """
    added = []
    changed = []
    seen = set()
    for row in rows:
        seen.add(row.drone_id)
        old = previous.get(row.drone_id)
        if old is None:
            added.append(row)
        elif old != row:
            changed.append(row)
    removed = sorted(drone_id for drone_id in previous if drone_id not in seen)
    return RowDiff(tuple(added), tuple(changed), tuple(removed))


def excess_lines(line_count: int, max_lines: int) -> int:
    """How many of the oldest log lines have to go to keep at most ``max_lines``.

    Args:
        line_count: Lines currently shown.
        max_lines: Limit; must be at least 1.

    Returns:
        0 if within the limit, else the number of lines to delete from the top.

    Raises:
        ValueError: If ``max_lines`` is below 1.
    """
    if max_lines < 1:
        raise ValueError(f"max_lines must be at least 1, got {max_lines}")
    return max(0, line_count - max_lines)
