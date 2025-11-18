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


from math import sqrt
from typing import Tuple, Optional

from .Animation import Animation
from .Color import Color
from .Command import Command
from .DroneAnimationSatus import DroneAnimationStatus
from .DroneStatus import DroneStatus
from .Point import Point


class Drone:
    _id: int
    animation: Animation
    _home_position: Point
    _position: Point
    _reported_position: Point
    _position_error: float
    _status: DroneStatus
    _animation_status: DroneAnimationStatus
    _battery: int
    _command: Command
    _animation_step: int

    def __init__(self, id: int, animation: Animation):
        self._id = id
        self.animation = animation
        self._home_position = animation.get_frame(0)[1]
        self._position = self._home_position
        self._reported_position = self._home_position
        self._status = DroneStatus.OK
        self._animation_status = DroneAnimationStatus.READY
        self._battery = -1
        self._command = Command.TELEMETRY_REQUEST
        self._position_error = 0
        self._animation_step = 0

    def __repr__(self) -> str:
        return f"Drone(id={self.id}, animation={self.animation})"

    def __lt__(self, other: 'Drone') -> bool:
        """Compare drones by id for sorting."""
        if not isinstance(other, Drone):
            return NotImplemented
        return self._id < other._id

    def __eq__(self, other: object) -> bool:
        """Check if two drones are equal based on id."""
        if not isinstance(other, Drone):
            return NotImplemented
        return self._id == other._id

    @property
    def id(self):
        return self._id

    @property
    def animation_len(self):
        return len(self.animation)

    @property
    def home_position(self):
        return self._home_position

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, position: Point):
        self._position = position

    @property
    def reported_position(self):
        return self._reported_position

    @reported_position.setter
    def reported_position(self, position: Point):
        self._reported_position = position

    @property
    def position_error(self):
        pos_error = sqrt((self._position.X - self._reported_position.X) ** 2 + (self._position.Y - self._reported_position.Y) ** 2 + (self._position.Z - self._reported_position.Z) ** 2)
        if pos_error == self._position_error:
            return self._position_error
        else:
            self._position_error = pos_error
            return self._position_error

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, command: Command):
        self._command = command

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status: DroneStatus):
        self._status = status

    @property
    def animation_status(self):
        return self._animation_status

    @animation_status.setter
    def animation_status(self, animation_status: DroneAnimationStatus):
        self._animation_status = animation_status

    @property
    def battery(self):
        return self._battery

    @battery.setter
    def battery(self, value: int):
        if 0 <= value <= 100:
            self._battery = value
        else:
            raise ValueError(f"Wrong battery input value, must be (0 <=> 100), got ({value}).")

    @property
    def animation_step(self):
        return self._animation_step

    @animation_step.setter
    def animation_step(self, step: int):
        if 0 <= step <= self.animation_len:
            self._animation_step = step
        else:
            raise ValueError(f"Wrong value, the step value:{step} will be ignored, animation step must be between 0 and {self.animation_len}")


    def get_frame(self, frame_index: int) -> Optional[Tuple[int, Point, Color]]:
        """
        Method for getting animation frame by index, in case of IndexError will return None.

        :param frame_index: The index of a frame

        :return: Tuple[timestamp, Point, Color] or None if index is out of range
        """
        return self.animation.get_frame(frame_index)

    def get_index(self, frame: Tuple[int, Point, Color]) -> Optional[int]:
        return self.animation.get_index(frame)
