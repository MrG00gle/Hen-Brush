
from enum import IntEnum

class PacketType(IntEnum):
    PING = 0x01
    PONG = 0x02
    DATA = 0x03
    ACK = 0x04  # Not Used
    POINT = 0x05
    COMMAND = 0x06
    TELEMETRY = 0x07
    ERROR = 0xFF    # Not Used
