"""A controller stand-in that records calls, for presenter and UI tests (no threads, no serial)."""

from typing import List, Optional, Tuple

from ControlTower.common import Drone


class StubController:
    """Implements the presenter's ``Controller`` protocol and records every call.

    Attributes:
        drones: The drones it pretends to run.
        calls: ``(action, drone ids)`` per call, in order.
        error: When set, every action raises it.
    """

    def __init__(self, drones: List[Drone]) -> None:
        self.drones = drones
        self.calls: List[Tuple[str, List[int]]] = []
        self.error: Optional[Exception] = None

    def _record(self, action: str, drones: Optional[List[Drone]]) -> None:
        if self.error is not None:
            raise self.error
        self.calls.append((action, [drone.id for drone in (self.drones if drones is None else drones)]))

    def start(self, drones: Optional[List[Drone]] = None) -> None:
        self._record("start", drones)

    def pause(self, drones: Optional[List[Drone]] = None) -> None:
        self._record("pause", drones)

    def stop(self, drones: Optional[List[Drone]] = None) -> None:
        self._record("stop", drones)
