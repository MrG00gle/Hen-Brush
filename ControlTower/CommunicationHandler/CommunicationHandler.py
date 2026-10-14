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
from typing import Generator, Optional, Union

from .payload import PointPayload, CPointPayload, CommandPayload, TelemetryPayload
from .PacketType import PacketType
from .CommunicationProtocol import CommunicationProtocol

logger = logging.getLogger(__name__)


class CommunicationHandler(CommunicationProtocol):
    """Sends drone payloads and listens for telemetry over a serial port.

    Attributes:
        port: Device name or pyserial URL the handler was opened with.
        timeout: Read timeout in seconds, also the pause between ``None`` items from ``listen``.
    """

    port: str
    timeout: float

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1) -> None:
        """Open the serial port.

        Args:
            port: Device name or pyserial URL (e.g. ``loop://`` for tests).
            baudrate: Port speed in baud.
            timeout: Read timeout in seconds.
        """
        self.port = port
        self.timeout = timeout
        super().__init__(port=port, baudrate=baudrate, timeout=timeout)

    def send(self, payload: Union[PointPayload, CPointPayload, CommandPayload]) -> None:
        """Send a payload without waiting for an ACK.

        Args:
            payload: Payload to send.

        Raises:
            ValueError: If the payload type cannot be sent.
        """
        logger.debug("Sending: %s", payload)

        match payload:
            case PointPayload():
                self.send_packet(PacketType.POINT, payload.payload)
            case CPointPayload():
                self.send_packet(PacketType.CPOINT, payload.payload)
            case CommandPayload():
                self.send_packet(PacketType.COMMAND, payload.payload)
            case _:
                raise ValueError(f"Payload can't be type: {type(payload)}")

    def listen(self) -> Generator[Optional[TelemetryPayload], None, None]:
        """Listen for telemetry packets until the port is closed.

        Yields:
            A ``TelemetryPayload`` for each telemetry packet, or None when no valid packet arrived
            within ``timeout`` or a telemetry payload could not be decoded. Consumers can use the
            None items to poll a stop flag. Packets of other types are skipped.
        """
        while self.ser.is_open:
            packet = self.read_packet(timeout=self.timeout)

            if packet:
                match packet['type']:
                    case PacketType.TELEMETRY:
                        try:
                            telemetry = TelemetryPayload(payload=packet['payload'])
                        except ValueError as error:
                            logger.warning("Malformed telemetry payload %s: %s", packet['payload'].hex(), error)
                            yield None
                            continue
                        logger.debug("Decoded: %s", telemetry)
                        yield telemetry
            else:
                yield None

    def close(self) -> None:
        """Close the serial port."""
        self.ser.close()
