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
from typing import List

from .common import *
from .Loader import Loader
from .Scheduler import Scheduler
from .CommunicationHandler import CommunicationHandler, PointPayload

class ControlTower:
    drones: List[Drone]
    comm: CommunicationHandler
    scheduler: Scheduler

    def __init__(self, path_to_animation: str, serial_port: str = None, serial_speed: int = None, serial_timeout: int = None):
        external_serial_port, external_serial_speed, external_serial_timeout, self.drones = Loader(path=path_to_animation).load()

        if serial_port and serial_speed and serial_timeout is not None:
            logging.info(f"Direct serial config detected.")
            self.comm = CommunicationHandler(serial_port, serial_speed, serial_timeout)
        elif external_serial_port and external_serial_speed and external_serial_timeout is not None:
            logging.info(f"External serial config detected.")
            self.comm = CommunicationHandler(external_serial_port, external_serial_speed, external_serial_timeout)
        else:
            logging.error(f"No serial config detected")
            raise SerialConfigLoadFailed(f"No serial config detected")

        self.scheduler = Scheduler(drones=self.drones, dispatcher_operation=self.__dispatch_operation, telemetry_operation=self.comm.listen)

    def __dispatch_operation(self, drone: Drone) -> None:
        drone_id = drone.id
        _, point, color = drone.get_frame(drone.animation_step)
        self.comm.send(PointPayload(drone_id, point, color))

    def start(self, drones: List[Drone]):
        self.scheduler.start(drones=drones)

    def pause(self, drones: List[Drone]):
        self.scheduler.pause(drones=drones)

    def stop(self, drones: List[Drone]):
        self.scheduler.stop(drones=drones)