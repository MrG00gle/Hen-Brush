"""GObject row item for the drone table. Needs PyGObject; the pure mapping lives in ``row_mapping``."""

from typing import Dict

from gi.repository import GObject

from .row_mapping import COLUMN_KEYS


class DroneItem(GObject.Object):
    """One drone in the ``Gio.ListStore`` behind the column view.

    The string properties match ``row_mapping.COLUMNS`` keys. The window updates them in place, and the
    labels bound to them follow through ``notify``. ``drone_id`` is not shown; it identifies the drone.
    """

    __gtype_name__ = "HenBrushDroneItem"

    drone_id = GObject.Property(type=int, default=0)
    id = GObject.Property(type=str, default="")
    status = GObject.Property(type=str, default="")
    animation_status = GObject.Property(type=str, default="")
    position = GObject.Property(type=str, default="")
    position_error = GObject.Property(type=str, default="")
    step = GObject.Property(type=str, default="")

    def __init__(self, drone_id: int, values: Dict[str, str]) -> None:
        """Create an item.

        Args:
            drone_id: Id of the drone this item shows.
            values: Column texts by key, from ``row_mapping.row_values``.
        """
        super().__init__()
        self.drone_id = drone_id
        self.update(values)

    def update(self, values: Dict[str, str]) -> None:
        """Set the column properties that differ, so unchanged cells don't emit ``notify``.

        Args:
            values: Column texts by key, from ``row_mapping.row_values``.
        """
        for key in COLUMN_KEYS:
            if getattr(self, key) != values[key]:
                setattr(self, key, values[key])
