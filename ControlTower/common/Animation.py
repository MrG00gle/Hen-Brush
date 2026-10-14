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
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Tuple

from .Color import Color
from .Point import Point

Frame = Tuple[int, Point, Color]


@dataclass
class Animation:
    """Flight path and light show of one drone, as parallel lists with one entry per frame.

    Attributes:
        timestamps: Time of each frame in milliseconds.
        flight_path: Position of the drone in each frame.
        colors: Color of the drone in each frame.
        path: File the animation was loaded from.
    """

    timestamps: List[int]
    flight_path: List[Point]
    colors: List[Color]
    path: Path

    def __init__(self, timestamps: List[int], flight_path: List[Point], colors: List[Color], path: Path) -> None:
        """Store the frame lists as given; they are expected to have the same length.

        Args:
            timestamps: Time of each frame in milliseconds.
            flight_path: Position of the drone in each frame.
            colors: Color of the drone in each frame.
            path: File the animation was loaded from.
        """
        self.timestamps = timestamps
        self.flight_path = flight_path
        self.colors = colors
        self.path = path

    def __repr__(self) -> str:
        if not self.timestamps:
            return f"Animation(empty, path={self.path})"
        return f"Animation(timestamp={self.timestamps[0]}, flight_path={self.flight_path[0]}, color={self.colors[0]}, path={self.path})"

    def __len__(self) -> int:
        return len(self.timestamps)

    def __iter__(self) -> Iterator[Frame]:
        for timestamp, point, color in zip(self.timestamps, self.flight_path, self.colors):
            yield timestamp, point, color

    def __reversed__(self) -> Iterator[Frame]:
        for timestamp, point, color in zip(reversed(self.timestamps), reversed(self.flight_path),
                                           reversed(self.colors)):
            yield timestamp, point, color

    def get_frame(self, index: int) -> Frame | None:
        """Get an animation frame by index.

        Args:
            index: Index of the frame, from 0 to ``len(self) - 1``. Negative indexes are out of range.

        Returns:
            ``(timestamp, point, color)``, or None if the index is out of range.
        """
        try:
            if index < 0:
                raise IndexError(index)  # Python would wrap around to the end of the lists
            timestamp = self.timestamps[index]
            point = self.flight_path[index]
            color = self.colors[index]
            return timestamp, point, color
        except IndexError:
            logging.error("Passed Animation index for Drone: %s, is out of range.", self.path.name)
            return None

    def get_index(self, frame: Frame) -> int | None:
        """Find the index of a frame. Only the timestamp of ``frame`` is compared.

        Args:
            frame: A ``(timestamp, point, color)`` tuple.

        Returns:
            Index of the first frame with the same timestamp, or None if there is none.
        """
        timestamp, _, _ = frame
        try:
            return self.timestamps.index(timestamp)
        except ValueError:
            logging.error("Passed frame is not present in Animation of Drone: %s", self.path.name)
            return None
