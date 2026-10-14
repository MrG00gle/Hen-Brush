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

import struct
from dataclasses import dataclass

from ControlTower.common import Command, Point, Color
from ._float16 import encode_float16


@dataclass
class CPointPayload:
    """Move a drone to a point and set its color (packet type CPOINT).

    Wire layout (11 bytes): drone_id (1) + command (1) + x, y, z (float16, 2 bytes each) + r, g, b (1 byte each).
    """

    _drone_id: int
    _command: Command
    _point: Point
    _color: Color
    _payload: bytes

    def __init__(self, drone_id: int, point: Point, color: Color, command: Command = Command.POSITION_COLOR) -> None:
        """Validate the arguments and encode the payload.

        Args:
            drone_id: Target drone id, 0-255.
            point: Target position; each coordinate must fit in float16 (|value| <= 65504).
            color: Target color; each channel must be an int in 0-255.
            command: Command byte to send with the point.

        Raises:
            ValueError: If the drone id, a color channel or a coordinate is invalid.
        """
        self._drone_id = drone_id
        self._command = command
        self._point = point
        self._color = color
        self.__create_payload()

    def __repr__(self) -> str:
        return f"CPointPayload(ID: {self._drone_id}, COMMAND: {self._command}, POINT: {self._point}, COLOR: {self._color}, PACKET: {self._payload.hex()})"

    def __create_payload(self) -> None:
        """Encode the payload: drone_id + command (1 byte each) + x, y, z (2 bytes each) + r, g, b (1 byte each), 11 bytes total.

        Raises:
            ValueError: If the drone id is not an int in 0-255.
            ValueError: If the command value is not in 0-255.
            ValueError: If a color channel is not an int in 0-255.
            ValueError: If a coordinate does not fit in float16.
        """
        # Validate integer inputs
        if not isinstance(self._drone_id, int) or not (0 <= self._drone_id <= 255):
            raise ValueError("Drone ID must be an integer between 0 and 255")

        if not isinstance(self._command.value, int) or not (0 <= self._command.value <= 255):
            raise ValueError("Command must be an integer between 0 and 255")

        if not isinstance(self._color.R, int) or not isinstance(self._color.G, int) or not isinstance(self._color.B, int) or \
                not (0 <= self._color.R <= 255 and 0 <= self._color.G <= 255 and 0 <= self._color.B <= 255):
            raise ValueError("RGB values must be integers between 0 and 255")

        x_bytes = encode_float16(self._point.X)
        y_bytes = encode_float16(self._point.Y)
        z_bytes = encode_float16(self._point.Z)

        # Pack data: B (unsigned char, 1 byte), 2s (2-byte string for float16), B for RGB
        self._payload = struct.pack(
            'BB2s2s2sBBB',
            self._drone_id,
            self._command.value,
            x_bytes,
            y_bytes,
            z_bytes,
            self._color.R,
            self._color.G,
            self._color.B
        )

    @property
    def drone_id(self) -> int:
        """Target drone id."""
        return self._drone_id

    @property
    def command(self) -> Command:
        """Command byte sent with the point."""
        return self._command

    @property
    def point(self) -> Point:
        """Target position."""
        return self._point

    @property
    def color(self) -> Color:
        """Target color."""
        return self._color

    @property
    def payload(self) -> bytes:
        """The encoded payload (11 bytes)."""
        return self._payload
