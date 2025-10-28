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

import numpy as np
from dataclasses import dataclass
from .Point import Point
from .Color import Color
from .DroneStatus import DroneStatus
from .DroneAnimationSatus import DroneAnimationStatus

@dataclass
class TelemetryPacket:
    _drone_id: int
    _point: Point
    _color: Color
    _drone_status: DroneStatus
    _drone_animation_status: DroneAnimationStatus
    _packet: bytes

    def __init__(self, packet: bytes):
        self._packet = packet
        self.__decode_packet()

    def __repr__(self) -> str:
        return f"TelemetryPacket(Id: {self._drone_id}, Point: {self._point}, Color: {self._color}, Drone_Status: {self._drone_status}, Drone_Anim_Status: {self._drone_animation_status})"

    def __decode_packet(self):
        """
        Decode a binary packet received over serial.

        Packet layout (12 bytes total):
          - drone_id                : uint8   (1 byte)
          - x, y, z (coordinates)  : float16 (2 bytes each)  → 6 bytes
          - r, g, b (color)        : uint8   (1 byte each)   → 3 bytes
          - drone_status           : uint8   (1 byte)
          - drone_animation_status : uint8   (1 byte)

        Parameters
        ----------
        packet: bytes
            Exactly 12 bytes read from the serial port.

        Raises
        ------
        struct.error
            If the byte string length is not 12.
        """

        if len(self._packet) != 12:
            raise ValueError(f"Expected 12 bytes, got {len(self._packet)}")

            # Interpret the entire byte string as uint8
        data = np.frombuffer(self._packet, dtype=np.uint8)

        drone_id = int(data[0])
        r, g, b = int(data[7]), int(data[8]), int(data[9])
        drone_status = int(data[10])
        drone_animation_status = int(data[11])

        # Reinterpret specific 2-byte regions as float16
        dtype = f'{'>'}f2'
        x = np.frombuffer(self._packet[1:3], dtype=dtype)[0]
        y = np.frombuffer(self._packet[3:5], dtype=dtype)[0]
        z = np.frombuffer(self._packet[5:7], dtype=dtype)[0]

        self._drone_id = drone_id
        self._point = Point(x=float(x), y=float(y), z=float(z))
        self._color = Color(r, g, b)
        self._drone_status = DroneStatus(drone_status)
        self._drone_animation_status = DroneAnimationStatus(drone_animation_status)


    @property
    def drone_id(self):
        return self._drone_id

    @property
    def point(self):
        return self._point

    @property
    def color(self):
        return self._color

    @property
    def drone_status(self):
        return self._drone_status

    @property
    def drone_animation_status(self):
        return self._drone_animation_status

    @property
    def packet(self):
        return self._packet