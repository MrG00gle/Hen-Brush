"""Fakes for Scheduler and ControlTower tests: a manual clock, telemetry builders and a fake comm."""

import struct
import threading
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence

import numpy as np

from ControlTower.CommunicationHandler import TelemetryPayload
from ControlTower.common import Animation, Color, Drone, DroneStatus, Point


class FakeClock:
    """Manual clock whose ``sleep`` advances time instantly and records every delay.

    Attributes:
        now: Current fake time in seconds.
        sleeps: Every value passed to ``sleep``, in call order.
    """

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: List[float] = []

    def __call__(self) -> float:
        """Return the fake time (usable as the ``clock`` argument)."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Record the delay and advance the fake time without waiting."""
        self.sleeps.append(seconds)
        self.now += seconds


def make_drone(drone_id: int, timestamps: Sequence[int] = (0, 100, 300, 600)) -> Drone:
    """Build a drone whose frame ``k`` is at ``Point(k, 0, 0)`` with color ``(k, 0, 0)``.

    Args:
        drone_id: Id of the drone (need not be contiguous with other drones).
        timestamps: Frame timestamps in milliseconds.

    Returns:
        The drone.
    """
    count = len(timestamps)
    animation = Animation(
        timestamps=list(timestamps),
        flight_path=[Point(float(k), 0.0, 0.0) for k in range(count)],
        colors=[Color(k, 0, 0) for k in range(count)],
        path=Path(f"drone_{drone_id}.csv"),
    )
    return Drone(id=drone_id, animation=animation)


def telemetry(drone_id: int, x: float = 2.0, status: DroneStatus = DroneStatus.OK) -> TelemetryPayload:
    """Build a telemetry payload for ``drone_id`` at ``(x, -1.5, 0.0)`` (big-endian float16 on the wire)."""
    position = np.array([x, -1.5, 0.0], dtype=">f2").tobytes()
    raw = struct.pack("B", drone_id) + position + bytes([255, 0, 128, status.value, 1])
    return TelemetryPayload(payload=raw)


class FakeComm:
    """Stand-in for ``CommunicationHandler`` that records sent payloads and replays telemetry.

    Attributes:
        sent: Every payload passed to ``send``, in order.
        closed: Whether ``close`` was called.
        drained: Set once every scripted telemetry item has been handled by the consumer.
    """

    def __init__(self, telemetry_items: Optional[Iterable[Optional[TelemetryPayload]]] = None) -> None:
        self.sent: List[object] = []
        self.closed = False
        self._telemetry = list(telemetry_items or [])
        self._closed_event = threading.Event()
        self.drained = threading.Event()

    def send(self, payload: object) -> None:
        """Record the payload."""
        self.sent.append(payload)

    def listen(self) -> Iterator[Optional[TelemetryPayload]]:
        """Yield the scripted telemetry, then None until the comm is closed."""
        yield from self._telemetry
        self.drained.set()  # reached only after the consumer finished handling the last scripted item
        while not self._closed_event.wait(0.001):
            yield None

    def close(self) -> None:
        """Mark the comm as closed and end ``listen``."""
        self.closed = True
        self._closed_event.set()
