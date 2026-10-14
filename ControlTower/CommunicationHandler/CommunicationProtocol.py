"""Frame-level serial protocol: header, type, length, payload, XOR checksum and footer."""
import logging
import struct
import time
from typing import Dict, Optional, Tuple, Union

import serial

from .PacketType import PacketType

logger = logging.getLogger(__name__)

Packet = Dict[str, Union[PacketType, bytes]]


class CommunicationProtocol:
    """Framed binary protocol over a serial port.

    Frame layout::

        HEADER (2) | type (1) | length (1) | payload (N) | checksum (1) | FOOTER (2)

    The checksum is the XOR of type, length and payload bytes. Incoming bytes are kept in a
    persistent buffer, so frames that arrive in pieces, or several frames in one read, are not lost.
    Bad wire data (wrong checksum, wrong footer, unknown packet type, garbage) is logged and skipped;
    it never raises.

    The port is opened with ``serial.serial_for_url``, so ``port`` may be a device name (``COM3``,
    ``/dev/ttyUSB0``) or a pyserial URL such as ``loop://``.

    Attributes:
        ser: The open serial port.
    """

    HEADER = b'\xAA\x55'
    FOOTER = b'\x55\xAA'
    MAX_PAYLOAD = 255
    # Header (2) + type (1) + length (1) + checksum (1) + footer (2)
    FRAME_OVERHEAD = 7

    ser: serial.SerialBase

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1) -> None:
        """Open the serial port.

        Args:
            port: Device name or pyserial URL.
            baudrate: Port speed in baud.
            timeout: Read timeout in seconds, passed to pyserial.
        """
        self.ser = serial.serial_for_url(port, baudrate=baudrate, timeout=timeout)
        self._rx_buffer = bytearray()

    def calculate_checksum(self, data: bytes) -> int:
        """Return the XOR of all bytes in ``data``."""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def create_packet(self, packet_type: int, payload: bytes = b'') -> bytes:
        """Build a complete frame.

        Args:
            packet_type: Packet type byte, usually a ``PacketType``.
            payload: Payload bytes.

        Returns:
            The frame ready to be written to the port.

        Raises:
            ValueError: If the payload is longer than 255 bytes.
        """
        length = len(payload)

        if length > self.MAX_PAYLOAD:
            raise ValueError("Payload too large")

        packet = self.HEADER
        packet += struct.pack('B', packet_type)
        packet += struct.pack('B', length)
        packet += payload

        checksum = self.calculate_checksum(packet[2:])  # Exclude header
        packet += struct.pack('B', checksum)
        packet += self.FOOTER

        return packet

    def send_packet(self, packet_type: int, payload: bytes = b'') -> bytes:
        """Build a frame, write it to the port and return it."""
        packet = self.create_packet(packet_type, payload)
        self.ser.write(packet)
        return packet

    def read_packet(self, timeout: float = 5) -> Optional[Packet]:
        """Wait for the next valid frame.

        Args:
            timeout: Seconds to wait for a complete, valid frame.

        Returns:
            A dict with ``type`` (``PacketType``), ``payload`` and ``raw`` (the whole frame), or
            None if no valid frame arrived within the timeout.
        """
        deadline = time.monotonic() + timeout

        while True:
            waiting = self.ser.in_waiting
            if waiting:
                self._rx_buffer += self.ser.read(waiting)

            packet, consumed = self._scan(bytes(self._rx_buffer))
            del self._rx_buffer[:consumed]
            if packet is not None:
                return packet

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            if not waiting:
                time.sleep(min(0.01, remaining))

    def parse_packet(self, buffer: bytes) -> Optional[Packet]:
        """Parse the first valid frame in ``buffer`` without touching the receive buffer.

        Args:
            buffer: Raw bytes, possibly with garbage around the frame.

        Returns:
            The packet dict (see ``read_packet``) or None if ``buffer`` holds no complete valid frame.
        """
        packet, _ = self._scan(buffer)
        return packet

    def _scan(self, buffer: bytes) -> Tuple[Optional[Packet], int]:
        """Find the first valid frame in ``buffer``.

        A frame with a bad footer, bad checksum or unknown type is dropped by skipping one byte
        past its header, then scanning resumes.

        Returns:
            The packet (or None) and how many leading bytes of ``buffer`` can be discarded.
        """
        position = 0

        while True:
            start = buffer.find(self.HEADER, position)
            if start == -1:
                # Keep a trailing lone first-header byte: the rest of the header may arrive next.
                keep_tail = 1 if buffer.endswith(self.HEADER[:1]) else 0
                return None, len(buffer) - keep_tail

            if len(buffer) < start + 4:
                return None, start

            payload_length = buffer[start + 3]
            total_length = self.FRAME_OVERHEAD + payload_length
            if len(buffer) < start + total_length:
                return None, start

            frame = bytes(buffer[start:start + total_length])
            reason = self._frame_problem(frame)
            if reason is not None:
                logger.warning("Dropping frame: %s (%s)", reason, frame.hex())
                position = start + 1
                continue

            return {
                'type': PacketType(frame[2]),
                'payload': frame[4:-3],
                'raw': frame,
            }, start + total_length

    def _frame_problem(self, frame: bytes) -> Optional[str]:
        """Describe what is wrong with a complete-length ``frame``, or None if it is valid."""
        if frame[-2:] != self.FOOTER:
            return "bad footer"

        expected_checksum = self.calculate_checksum(frame[2:-3])  # Type + length + payload
        if expected_checksum != frame[-3]:
            return f"checksum mismatch, expected {expected_checksum}, got {frame[-3]}"

        try:
            PacketType(frame[2])
        except ValueError:
            return f"unknown packet type {frame[2]:#04x}"

        return None

    def close(self) -> None:
        """Close the serial port."""
        self.ser.close()
