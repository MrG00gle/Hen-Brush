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
import pathlib
from dataclasses import dataclass
from typing import Tuple, List, Optional

from .Color import Color
from .Point import Point


@dataclass
class Animation:
    timestamps: List[int]
    flight_path: List[Point]
    colors: List[Color]
    path: pathlib.Path or pathlib.WindowsPath

    def __init__(self, timestamps: List[int], flight_path: List[Point], colors: List[Color], path: pathlib.Path or pathlib.WindowsPath) -> None:
        self.timestamps = timestamps
        self.flight_path = flight_path
        self.colors = colors
        self.path = path

    def __repr__(self) -> str:
        return f"Animation(timestamp={self.timestamps[0]}, flight_path={self.flight_path[0]}, color={self.colors[0]}, path={self.path})"

    def __len__(self) -> int:
        return len(self.timestamps)

    def __iter__(self):
        for timestamp, point, color in zip(self.timestamps, self.flight_path, self.colors):
            yield timestamp, point, color

    def __reversed__(self):
        for timestamp, point, color in zip(reversed(self.timestamps), reversed(self.flight_path),
                                           reversed(self.colors)):
            yield timestamp, point, color

    def get_frame(self, index: int) -> Tuple[int, Point, Color] | None:
        """
        Method for getting animation frame by index, in case of IndexError will return None.

        :param index: The index of a frame

        :return: Tuple[int, Point, Color] and None if index is out of range
        """
        try:
            timestamp = self.timestamps[index]
            point = self.flight_path[index]
            color = self.colors[index]
            return timestamp, point, color
        except IndexError:
            logging.error(f"Passed Animation index for Drone: {self.path.name}, is out of range.")
            return None


    def get_index(self, frame: Tuple[int, Point, Color]) -> Optional[int]:
        timestamp, _, _ = frame
        try:
            return self.timestamps.index(timestamp)
        except ValueError:
            logging.error(f"Passed frame is not present in Animation of Drone: {self.path.name}")
