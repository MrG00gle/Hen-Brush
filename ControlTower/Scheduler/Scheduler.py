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

from ControlTower.CommunicationHandler.payload import TelemetryPayload
from ControlTower.common import *


class Scheduler:

    dispatcher_threads: List[Thread]
    listener_thread: Thread
    drones: List[Drone]

    def __init__(self, drones: List[Drone], dispatcher_operation: Callable[[Drone], None], telemetry_operation: Callable[[], Iterable[TelemetryPayload]], daemon: bool = False):
        self.drones = drones
        self.dispatcher_threads = []
        self.add_dispatcher_thread(operation=dispatcher_operation, drones=self.drones, daemon=daemon)
        self.listener_thread = Thread(name="Listener", target=self.__listener_thread, args=(telemetry_operation, ))

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

    def __listener_thread(self, telemetry_operation: Callable[[], Iterable[TelemetryPayload]]):
        for payload in telemetry_operation():
            if type(payload) is TelemetryPayload:
                drone = self.drones[payload.drone_id]
                drone.status = payload.drone_status
                drone.reported_position = payload.point

    def add_dispatcher_thread(self, operation: Callable[[Drone], None], drones: List[Drone], daemon: bool = False):
        for drone in drones:
            self.dispatcher_threads.append(Thread(name=f"Dispatcher_Drone({drone.id})", target=self.__dispatcher_thread, args=(drone, operation), daemon=daemon))
        self.dispatcher_threads.sort(key=lambda thread: int(thread.name))

    def start(self, drones: List[Drone] = None):
        self.listener_thread.start()
        if drones is None:
            for drone in self.drones:
               self.dispatcher_threads[drone.id].start()
        else:
            for drone in drones:
               self.dispatcher_threads[drone.id].start()

    def pause(self, drone: List[Drone] | Drone):
        if type(drone) is list:
            for d in drone:
                d.animation_status = DroneAnimationStatus.PAUSED
        elif type(drone) is Drone:
            drone.animation_status = DroneAnimationStatus.PAUSED

    def stop(self, drone: List[Drone] | Drone):
        if type(drone) is list:
            for d in drone:
                d.animation_status = DroneAnimationStatus.ENDED
        elif type(drone) is Drone:
            drone.animation_status = DroneAnimationStatus.ENDED
