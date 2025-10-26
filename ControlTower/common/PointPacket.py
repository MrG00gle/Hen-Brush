

import struct
import numpy as np
from dataclasses import dataclass

from .Command import Command
from .Point import Point
from .Color import Color


@dataclass
class PointPacket:
    _drone_id: int
    _command: Command
    _point: Point
    _color: Color
    _packet: bytes

    def __init__(self, drone_id: int, point: Point, color: Color, command: Command = Command.POSITION):
        self._drone_id = drone_id
        self._command = command
        self._point = point
        self._color = color
        self.__create_packet()

    def __create_packet(self):
        """
        Creates a binary packet for drone communication using half-precision floats.
        """

        # Validate integer inputs
        if not isinstance(self._drone_id, int) or not (0 <= self._drone_id <= 255):
            raise ValueError("Drone ID must be an integer between 0 and 255")
        if not isinstance(self._command.value, int) or not (0 <= self._command.value <= 255):
            raise ValueError("Command must be an integer between 0 and 255")
        if not isinstance(self._color.R, int) or not isinstance(self._color.G, int) or not isinstance(self._color.B, int) or \
                not (0 <= self._color.R <= 255 and 0 <= self._color.G <= 255 and 0 <= self._color.B <= 255):
            raise ValueError("RGB values must be integers between 0 and 255")

        # Convert floats to float16 using NumPy
        try:
            x_float16 = np.float16(self._point.X)
            y_float16 = np.float16(self._point.Y)
            z_float16 = np.float16(self._point.Z)
        except (OverflowError, ValueError) as e:
            raise ValueError("Float values out of range for float16") from e

        # Convert float16 to bytes (2 bytes each)
        x_bytes = np.float16(self._point.X).tobytes()
        y_bytes = np.float16(self._point.Y).tobytes()
        z_bytes = np.float16(self._point.Z).tobytes()

        # Pack data: B (unsigned char, 1 byte), 2s (2-byte string for float16), B for RGB
        self._packet = struct.pack(
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
    def drone_id(self):
        return self._drone_id

    @property
    def command(self):
        return self._command

    @property
    def point(self):
        return self._point

    @property
    def color(self):
        return self._color

    @property
    def packet(self):
        return self._packet