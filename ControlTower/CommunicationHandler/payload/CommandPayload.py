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

from ControlTower.common import Command


@dataclass
class CommandPayload:
    """Send a command to a drone (packet type COMMAND).

    Wire layout (2 bytes): drone_id (1) + command (1).
    """

    _drone_id: int
    _command: Command
    _payload: bytes

    def __init__(self, drone_id: int, command: Command) -> None:
        """Validate the arguments and encode the payload.

        Args:
            drone_id: Target drone id, 0-255.
            command: Command to send; its value is used verbatim as the command byte.

        Raises:
            ValueError: If the drone id is not an int in 0-255 or the command value is not in 0-255.
        """
        self._drone_id = drone_id
        self._command = command
        self.__create_payload()

    def __repr__(self) -> str:
        return f"CommandPayload(ID: {self._drone_id}, COMMAND: {self._command.value}, PACKET: {self._payload.hex()})"

    def __create_payload(self) -> None:
        """Encode the payload: drone_id (1 byte) + command (1 byte).

        Raises:
            ValueError: If the drone id is not an int in 0-255.
            ValueError: If the command value is not in 0-255.
        """
        if not isinstance(self._drone_id, int) or not (0 <= self._drone_id <= 255):
            raise ValueError("Drone ID must be an integer between 0 and 255")

        if not 0 <= self._command.value <= 255:
            raise ValueError("command must be between 0 and 255")

        # Pack data: B (unsigned char, 1 byte)
        self._payload = struct.pack(
            'BB',
            self._drone_id,
            self._command.value
        )

    @property
    def drone_id(self) -> int:
        """Target drone id."""
        return self._drone_id

    @property
    def command(self) -> Command:
        """Command sent to the drone."""
        return self._command

    @property
    def payload(self) -> bytes:
        """The encoded payload (2 bytes)."""
        return self._payload
