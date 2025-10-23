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
from typing import List

from ..common import *


class SimpleScheduler:

    threads: List[Thread]

    def __init__(self):
        pass

    def thread(self, drone: Drone, operation):
        for step in range(drone.animation_len):

            if step == drone.animation_len:
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


    def add_thread(self, operation, drone: Drone):
        self.threads.append(Thread(name=str(drone.id), target=self.thread, args=(drone, operation)))
