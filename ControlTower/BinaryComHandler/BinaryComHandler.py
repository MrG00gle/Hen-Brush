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

from typing import Union

from ..common import *
from .payload import *
from .PacketType import PacketType
from .BinaryProtocol import BinaryProtocol

log = get_logger(__name__)

class BinaryComHandler(BinaryProtocol):

    def __init__(self, port: str, baudrate: int = 115200):
        super().__init__(port=port, baudrate=baudrate)

    def send_data(self, payload: Union[PointPayload, CommandPayload]):
        """Send data packet"""
        log.comm(f"Sending data: {payload}")
        if type(payload) is PointPayload:
            self.send_packet(PacketType.POINT, payload)
        elif type(payload) is CommandPayload:
            self.send_packet(PacketType.COMMAND, payload)

        # Wait for ACK
        response = self.read_packet()
        if response and response['type'] == PacketType.ACK:
            log.comm("✅ Data acknowledged")
            return True
        else:
            log.comm("❌ No acknowledgment")
            return False