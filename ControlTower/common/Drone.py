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


from math import dist

from .Animation import Animation, Frame
from .Color import Color
from .Command import Command
from .DroneAnimationSatus import DroneAnimationStatus
from .DroneStatus import DroneStatus
from .Point import Point


class Drone:
    """A drone with its animation and the state last known about it.

    Drones are equal, hashable and sortable by ``id`` only.

    Attributes:
        animation: The animation this drone flies.
    """

    _id: int
    animation: Animation
    _home_position: Point
    _position: Point
    _reported_position: Point
    _status: DroneStatus
    _animation_status: DroneAnimationStatus
    _battery: int
    _command: Command
    _animation_step: int

    def __init__(self, id: int, animation: Animation) -> None:
        """Create a drone parked at the first frame of its animation.

        Args:
            id: Drone id.
            animation: Animation to fly; must have at least one frame.

        Raises:
            ValueError: If the animation has no frames.
        """
        if len(animation) == 0:
            raise ValueError(f"Drone {id} needs an animation with at least one frame, got an empty one: {animation.path}")

        self._id = id
        self.animation = animation
        self._home_position = animation.flight_path[0]
        self._position = self._home_position
        self._reported_position = self._home_position
        self._status = DroneStatus.OK
        self._animation_status = DroneAnimationStatus.READY
        self._battery = -1
        self._command = Command.TELEMETRY_REQUEST
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

    def __hash__(self) -> int:
        """Hash by id, consistent with ``__eq__``."""
        return hash(self._id)

    @property
    def id(self) -> int:
        """Drone id."""
        return self._id

    @property
    def animation_len(self) -> int:
        """Number of frames in the animation."""
        return len(self.animation)

    @property
    def home_position(self) -> Point:
        """Position of the first animation frame."""
        return self._home_position

    @property
    def position(self) -> Point:
        """Position the drone is expected to be at."""
        return self._position

    @position.setter
    def position(self, position: Point) -> None:
        self._position = position

    @property
    def reported_position(self) -> Point:
        """Position last reported by the drone's telemetry."""
        return self._reported_position

    @reported_position.setter
    def reported_position(self, position: Point) -> None:
        self._reported_position = position

    @property
    def position_error(self) -> float:
        """Distance in 3D between the expected and the reported position."""
        return dist(
            (self._position.X, self._position.Y, self._position.Z),
            (self._reported_position.X, self._reported_position.Y, self._reported_position.Z),
        )

    @property
    def command(self) -> Command:
        """Command last sent to the drone."""
        return self._command

    @command.setter
    def command(self, command: Command) -> None:
        self._command = command

    @property
    def status(self) -> DroneStatus:
        """Health status of the drone."""
        return self._status

    @status.setter
    def status(self, status: DroneStatus) -> None:
        self._status = status

    @property
    def animation_status(self) -> DroneAnimationStatus:
        """Playback state of the animation."""
        return self._animation_status

    @animation_status.setter
    def animation_status(self, animation_status: DroneAnimationStatus) -> None:
        self._animation_status = animation_status

    @property
    def battery(self) -> int:
        """Battery level in percent (0-100), or -1 while unknown.

        Raises:
            ValueError: When set to a value outside 0-100.
        """
        return self._battery

    @battery.setter
    def battery(self, value: int) -> None:
        if 0 <= value <= 100:
            self._battery = value
        else:
            raise ValueError(f"Wrong battery input value, must be (0 <=> 100), got ({value}).")

    @property
    def animation_step(self) -> int:
        """Index of the current animation frame.

        Raises:
            ValueError: When set to a value outside ``0 <= step < animation_len``.
        """
        return self._animation_step

    @animation_step.setter
    def animation_step(self, step: int) -> None:
        if 0 <= step < self.animation_len:
            self._animation_step = step
        else:
            raise ValueError(f"Wrong value, the step value:{step} will be ignored, animation step must be between 0 and {self.animation_len - 1}")

    def get_frame(self, frame_index: int) -> Frame | None:
        """Get an animation frame by index.

        Args:
            frame_index: Index of the frame.

        Returns:
            ``(timestamp, point, color)``, or None if the index is out of range.
        """
        return self.animation.get_frame(frame_index)

    def get_index(self, frame: Frame) -> int | None:
        """Find the index of a frame in the animation.

        Args:
            frame: A ``(timestamp, point, color)`` tuple; only the timestamp is compared.

        Returns:
            The index, or None if the animation has no frame with that timestamp.
        """
        return self.animation.get_index(frame)
