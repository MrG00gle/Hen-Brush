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

import time
from threading import Thread
from typing import List, Callable, Iterable

from ..CommunicationHandler.payload import TelemetryPayload
from ..common import *


class Scheduler:

    threads: List[Thread]
    drones: List[Drone]

    def __init__(self, drones: List[Drone], dispatcher_operation: Callable[[Drone], None], daemon: bool = False):
        self.drones = drones
        self.threads = []
        self.add_dispatcher_thread(operation=dispatcher_operation, drones=self.drones, daemon=daemon)

    def __dispatcher_thread(self, drone: Drone, operation: Callable[[Drone], None]):
        drone.animation_status = DroneAnimationStatus.LIVE
        for step in range(drone.animation_len):

            if step == drone.animation_len - 1:
                s_duration = float(abs(drone.get_frame(step)[0] - drone.get_frame(step - 1)[0])) / 1000
            else:
                s_duration = float(abs(drone.get_frame(step + 1)[0] - drone.get_frame(step)[0])) / 1000

            time.sleep(s_duration)

            match drone.animation_status:
                case DroneAnimationStatus.LIVE:
                    operation(drone)
                    drone.animation_step = step
                case DroneAnimationStatus.PAUSED:
                    drone.animation_step = step
                    continue
                case DroneAnimationStatus.ENDED:
                    break
                case _:
                    continue

    def __listener_thread(self, operation: Callable[[], Iterable[TelemetryPayload]]):
        pass

    def add_dispatcher_thread(self, operation: Callable[[Drone], None], drones: List[Drone], daemon: bool = False):
        for drone in drones:
            self.threads.append(Thread(name=str(drone.id), target=self.__dispatcher_thread, args=(drone, operation), daemon=daemon))
        self.threads.sort(key=lambda thread: int(thread.name))

    def start(self, drones: List[Drone] = None):
        if drones is None:
            for drone in self.drones:
               self.threads[drone.id].start()
        else:
            for drone in drones:
               self.threads[drone.id].start()

    def pause(self, drones: List[Drone]):
        for drone in drones:
            drone.animation_status = DroneAnimationStatus.PAUSED

    def stop(self, drones: List[Drone] = None):
        if drones is None:
            for drone in self.drones:
                drone.animation_status = DroneAnimationStatus.ENDED
        else:
            for drone in drones:
                drone.animation_status = DroneAnimationStatus.ENDED
