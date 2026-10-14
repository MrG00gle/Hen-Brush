"""Packet type identifiers of the serial protocol."""
from enum import IntEnum
class PacketType(IntEnum):
    """Packet type byte of a serial frame. The values are part of the wire protocol."""

    PING = 0x01
    PONG = 0x02
    DATA = 0x03
    ACK = 0x04  # Not Used
    POINT = 0x05
    CPOINT = 0x06
    COMMAND = 0x07
    TELEMETRY = 0x08
    ERROR = 0xFF    # Not Used
