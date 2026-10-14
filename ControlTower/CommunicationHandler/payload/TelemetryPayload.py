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

from ControlTower.common import Point, Color, DroneStatus


@dataclass
class TelemetryPayload:
    """Telemetry reported by a drone (packet type TELEMETRY), decoded from 12 bytes."""

    _drone_id: int
    _point: Point
    _color: Color
    _drone_status: DroneStatus
    _payload: bytes

    def __init__(self, payload: bytes) -> None:
        """Decode a received payload.

        Args:
            payload: Exactly 12 bytes read from the serial port.

        Raises:
            ValueError: If the payload is not 12 bytes long or the status byte is not a known DroneStatus.
        """
        self._payload = payload
        self.__decode_payload()

    def __repr__(self) -> str:
        return f"TelemetryPayload(Id: {self._drone_id}, Point: {self._point}, Color: {self._color}, Drone_Status: {self._drone_status})"

    def __decode_payload(self) -> None:
        """Decode the binary payload.

        Payload layout (12 bytes total):
          - byte 0: drone_id, uint8
          - bytes 1-6: x, y, z, big-endian float16 (2 bytes each)
          - bytes 7-9: r, g, b, uint8 (1 byte each)
          - byte 10: drone_status, uint8 (see DroneStatus)
          - byte 11: animation status, NOT decoded. The byte must be present but its value is ignored.

        Note:
            Telemetry floats are decoded big-endian while Point and CPoint payloads are encoded
            little-endian. This asymmetry is kept as-is because the firmware is not part of this repository.

        Raises:
            ValueError: If the payload is not 12 bytes long.
            ValueError: If the status byte is not a known DroneStatus.
        """
        if len(self._payload) != 12:
            raise ValueError(f"Expected 12 bytes, got {len(self._payload)}")

        # Interpret the entire byte string as uint8
        data = np.frombuffer(self._payload, dtype=np.uint8)

        drone_id = int(data[0])
        r, g, b = int(data[7]), int(data[8]), int(data[9])
        drone_status = int(data[10])

        # Reinterpret specific 2-byte regions as big-endian float16
        dtype = '>f2'
        x = np.frombuffer(self._payload[1:3], dtype=dtype)[0]
        y = np.frombuffer(self._payload[3:5], dtype=dtype)[0]
        z = np.frombuffer(self._payload[5:7], dtype=dtype)[0]

        self._drone_id = drone_id
        self._point = Point(x=float(x), y=float(y), z=float(z))
        self._color = Color(r, g, b)
        self._drone_status = DroneStatus(drone_status)

    @property
    def drone_id(self) -> int:
        """Id of the reporting drone."""
        return self._drone_id

    @property
    def point(self) -> Point:
        """Reported position."""
        return self._point

    @property
    def color(self) -> Color:
        """Reported color."""
        return self._color

    @property
    def drone_status(self) -> DroneStatus:
        """Reported drone status."""
        return self._drone_status

    @property
    def payload(self) -> bytes:
        """The raw payload this object was decoded from."""
        return self._payload
