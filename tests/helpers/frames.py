"""Independent construction of wire frames, so tests do not reuse the code under test."""

from functools import reduce


def build_frame(packet_type: int, payload: bytes = b"") -> bytes:
    """Build ``AA 55 | type | len | payload | xor(type, len, payload) | 55 AA``.

    Args:
        packet_type: Packet type byte.
        payload: Payload bytes (at most 255).

    Returns:
        The complete frame.
    """
    body = bytes([packet_type, len(payload)]) + payload
    checksum = reduce(lambda acc, byte: acc ^ byte, body, 0)
    return b"\xAA\x55" + body + bytes([checksum]) + b"\x55\xAA"
