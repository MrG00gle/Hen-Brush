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
from typing import Union, ByteString

from ..common import *
from .payload import *
from .PacketType import PacketType
from .CommunicationProtocol import CommunicationProtocol


class CommunicationHandler(CommunicationProtocol):

    port: str
    timeout: int

    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 1):
        self.port = port
        self.timeout = timeout
        super().__init__(port=port, baudrate=baudrate, timeout=timeout)

    def send(self, payload: Union[PointPayload, CommandPayload]) -> None:
        """
            Send data packet without waiting on ACK
        """
        logging.debug(f"Sending: {payload}")

        match payload:
            case PointPayload():
                self.send_packet(PacketType.POINT, payload.payload)
            case CommandPayload():
                self.send_packet(PacketType.COMMAND, payload.payload)
            case _:
                raise ValueError(f"Payload can't be type: {type(payload)}")

    def listen(self) -> TelemetryPayload | None:
        """
            Listen for Telemetry packets, parse and return Telemetry Payload
        """

        packet = self.read_packet(timeout=self.timeout)

        if packet:
            packet_type = packet['type']
            payload = packet['payload']

            match packet_type:
                case PacketType.TELEMETRY:
                    telemetry = TelemetryPayload(payload=payload)
                    logging.debug(f"Got: {telemetry}")
                    return telemetry
        else:
            return None

    def close(self):
        self.ser.close()
