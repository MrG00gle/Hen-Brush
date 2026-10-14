"""
// Copyright (C) 2025 Matsvei Kuzmiankou
//
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 3 of the License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with this program; if not, write to the Free Software Foundation,
// Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import logging
import time
from typing import Callable, List, Optional

from .common import Drone, Point, SerialConfigLoadFailed
from .Loader import Loader
from .Scheduler import Scheduler
from .CommunicationHandler import CommunicationHandler, PointPayload, CPointPayload

logger = logging.getLogger(__name__)


class ControlTower:
    """Facade that loads animations, talks to the drones and schedules their playback.

    Serial configuration precedence: a complete direct configuration (port, speed and timeout all
    given, ``0`` counts as given) wins over the ``*.json`` file in the animation directory; if
    neither is complete, ``SerialConfigLoadFailed`` is raised. An injected ``comm`` needs no
    serial configuration at all.

    Attributes:
        drones: Drones loaded from the animation directory.
        comm: The communication handler used to send commands and receive telemetry.
        scheduler: The scheduler playing the animations.
    """

    drones: List[Drone]
    comm: CommunicationHandler
    scheduler: Scheduler

    def __init__(
            self,
            path_to_animation: str,
            serial_port: Optional[str] = None,
            serial_speed: Optional[int] = None,
            serial_timeout: Optional[float] = None,
            *,
            comm: Optional[CommunicationHandler] = None,
            sleep: Optional[Callable[[float], None]] = None,
            clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Load the animations and open the serial connection.

        Args:
            path_to_animation: Directory with the drone CSV files and optional JSON config.
            serial_port: Serial port (direct configuration).
            serial_speed: Serial speed in baud (direct configuration).
            serial_timeout: Serial read timeout in seconds (direct configuration).
            comm: Ready-made communication handler (or a fake in tests). When given, no serial
                port is opened and no serial configuration is needed.
            sleep: Passed to the ``Scheduler`` to replace the wait between frames (tests).
            clock: Passed to the ``Scheduler`` as its clock (tests).

        Raises:
            FileNotFoundError: If ``path_to_animation`` does not exist.
            NotADirectoryError: If ``path_to_animation`` is not a directory.
            SerialConfigLoadFailed: If no complete serial configuration is available.
        """
        file_port, file_speed, file_timeout, self.drones = Loader(path=path_to_animation).load()

        if comm is not None:
            self.comm = comm
        else:
            direct = (serial_port, serial_speed, serial_timeout)
            from_file = (file_port, file_speed, file_timeout)
            if all(value is not None for value in direct):
                logger.info("Direct serial config detected.")
                self.comm = CommunicationHandler(*direct)
            elif all(value is not None for value in from_file):
                if any(value is not None for value in direct):
                    logger.warning("Incomplete direct serial config (port, speed and timeout are all needed), using the config file.")
                logger.info("External serial config detected.")
                self.comm = CommunicationHandler(*from_file)
            else:
                logger.error("No serial config detected")
                raise SerialConfigLoadFailed("No serial config detected")

        self.scheduler = Scheduler(
            drones=self.drones,
            dispatcher_operation=self._dispatch_operation,
            telemetry_operation=self.comm.listen,
            sleep=sleep,
            clock=clock,
        )

    def _dispatch_operation(self, drone: Drone) -> None:
        """Send the frame the drone is currently at (``drone.animation_step``) as a CPOINT packet."""
        _, point, color = drone.get_frame(drone.animation_step)
        self.comm.send(CPointPayload(drone.id, point, color))

    def send_to_point(self, drones: List[Drone], points: List[Point]) -> None:
        """Send each drone to the point at the same index.

        Nothing is sent if the lists differ in length or a point can't be encoded.

        Args:
            drones: Drones to move.
            points: Target point of each drone.

        Raises:
            ValueError: If the lists differ in length, or a point does not fit the payload.
        """
        if len(drones) != len(points):
            raise ValueError(f"Got {len(drones)} drones but {len(points)} points")

        payloads = [PointPayload(drone.id, point) for drone, point in zip(drones, points, strict=True)]
        for payload, point in zip(payloads, points, strict=True):
            self.comm.send(payload)
            logger.info("Sending Drone(%s) to Point(%s)", payload.drone_id, point)

    @staticmethod
    def _ids(drones: List[Drone]) -> str:
        return ", ".join(str(drone.id) for drone in drones)

    def start(self, drones: Optional[List[Drone]] = None) -> None:
        """Start, or resume, the animation of drones.

        Args:
            drones: Drones to start; None starts all of them.
        """
        self.scheduler.start(drones=drones)
        logger.info("Starting animation for Drones(%s)", self._ids(drones if drones is not None else self.drones))

    def pause(self, drones: Optional[List[Drone]] = None) -> None:
        """Pause the animation of drones.

        Args:
            drones: Drones to pause; None pauses all of them.
        """
        self.scheduler.pause(drones=drones)
        logger.info("Pausing animation for Drones(%s)", self._ids(drones if drones is not None else self.drones))

    def stop(self, drones: Optional[List[Drone]] = None) -> None:
        """Stop the animation of drones.

        Args:
            drones: Drones to stop; None stops all of them.
        """
        self.scheduler.stop(drones=drones)
        logger.info("Stopping animation for Drones(%s)", self._ids(drones if drones is not None else self.drones))

    def shutdown(self) -> None:
        """Stop the scheduler and close the communication handler. Call when the UI exits."""
        self.scheduler.shutdown()
        self.comm.close()
