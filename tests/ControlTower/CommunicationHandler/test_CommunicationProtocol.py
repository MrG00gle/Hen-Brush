import time

import pytest
import serial

from ControlTower.CommunicationHandler import CommunicationProtocol, PacketType
from tests.helpers.frames import build_frame

TELEMETRY_BYTES = bytes(range(12))


@pytest.fixture
def protocol(monkeypatch, fake_serial):
    monkeypatch.setattr(serial, "serial_for_url", lambda *args, **kwargs: fake_serial)
    return CommunicationProtocol(port="fake://", timeout=0.05)


class TestPacketType:

    @pytest.mark.parametrize(
        "name, value",
        [
            ("PING", 0x01), ("PONG", 0x02), ("DATA", 0x03), ("ACK", 0x04), ("POINT", 0x05),
            ("CPOINT", 0x06), ("COMMAND", 0x07), ("TELEMETRY", 0x08), ("ERROR", 0xFF),
        ],
    )
    def test_wire_values(self, name, value):
        assert PacketType[name] == value
        assert PacketType(value) is PacketType[name]


class TestConstruction:

    def test_uses_serial_for_url(self, monkeypatch, fake_serial):
        calls = []

        def fake_for_url(*args, **kwargs):
            calls.append((args, kwargs))
            return fake_serial

        monkeypatch.setattr(serial, "serial_for_url", fake_for_url)
        proto = CommunicationProtocol("loop://", baudrate=57600, timeout=0.25)

        assert proto.ser is fake_serial
        assert calls == [(("loop://",), {"baudrate": 57600, "timeout": 0.25})]

    def test_loop_url_opens_a_real_port(self, loop_serial_url):
        proto = CommunicationProtocol(loop_serial_url, timeout=0.05)
        try:
            assert proto.ser.is_open
        finally:
            proto.close()
        assert not proto.ser.is_open


class TestFraming:

    def test_hand_built_frame_matches_expected_bytes(self, protocol):
        frame = protocol.create_packet(PacketType.COMMAND, bytes([0x02, 0x03]))

        assert frame == bytes([0xAA, 0x55, 0x07, 0x02, 0x02, 0x03, 0x04, 0x55, 0xAA])

    def test_empty_payload(self, protocol):
        assert protocol.create_packet(PacketType.PING) == bytes.fromhex("aa5501000155aa")

    @pytest.mark.parametrize("length", [0, 1, 254, 255])
    def test_payload_up_to_255_bytes_is_accepted(self, protocol, length):
        payload = bytes([0x11]) * length
        frame = protocol.create_packet(PacketType.DATA, payload)

        assert frame == build_frame(PacketType.DATA, payload)
        assert frame[3] == length

    @pytest.mark.parametrize("length", [256, 300])
    def test_oversize_payload_raises(self, protocol, length):
        with pytest.raises(ValueError, match="too large"):
            protocol.create_packet(PacketType.DATA, bytes(length))

    def test_send_packet_writes_the_frame(self, protocol, fake_serial):
        returned = protocol.send_packet(PacketType.POINT, b"\x01\x02")

        assert returned == build_frame(PacketType.POINT, b"\x01\x02")
        assert fake_serial.written == [returned]

    @pytest.mark.parametrize(
        "data, expected",
        [(b"", 0), (b"\x01", 1), (b"\x01\x01", 0), (b"\x07\x02\x02\x03", 0x04), (b"\xff\x0f", 0xF0)],
    )
    def test_checksum_is_xor(self, protocol, data, expected):
        assert protocol.calculate_checksum(data) == expected


class TestReading:

    def test_valid_frame(self, protocol, fake_serial):
        frame = build_frame(PacketType.TELEMETRY, TELEMETRY_BYTES)
        fake_serial.feed(frame)

        packet = protocol.read_packet(timeout=0.5)

        assert packet == {"type": PacketType.TELEMETRY, "payload": TELEMETRY_BYTES, "raw": frame}

    def test_empty_payload_frame(self, protocol, fake_serial):
        fake_serial.feed(build_frame(PacketType.PING))

        packet = protocol.read_packet(timeout=0.5)

        assert packet["type"] == PacketType.PING
        assert packet["payload"] == b""

    def test_checksum_mismatch_returns_none(self, protocol, fake_serial):
        frame = bytearray(build_frame(PacketType.POINT, b"\x01\x02\x03"))
        frame[-3] ^= 0xFF
        fake_serial.feed(bytes(frame))

        assert protocol.read_packet(timeout=0.05) is None

    def test_bad_footer_returns_none(self, protocol, fake_serial):
        frame = bytearray(build_frame(PacketType.POINT, b"\x01\x02\x03"))
        frame[-1] = 0x00
        fake_serial.feed(bytes(frame))

        assert protocol.read_packet(timeout=0.05) is None

    def test_good_frame_after_bad_checksum_is_still_found(self, protocol, fake_serial):
        bad = bytearray(build_frame(PacketType.POINT, b"\x01\x02"))
        bad[-3] ^= 0x01
        good = build_frame(PacketType.COMMAND, b"\x05\x06")
        fake_serial.feed(bytes(bad) + good)

        packet = protocol.read_packet(timeout=0.5)

        assert packet["raw"] == good

    def test_partial_frame_in_two_chunks(self, protocol, fake_serial):
        frame = build_frame(PacketType.CPOINT, bytes(range(11)))
        fake_serial.feed_chunks(frame[:5], frame[5:])

        packet = protocol.read_packet(timeout=0.5)

        assert packet["raw"] == frame

    def test_partial_frame_in_three_chunks(self, protocol, fake_serial):
        frame = build_frame(PacketType.CPOINT, bytes(range(11)))
        fake_serial.feed_chunks(frame[:3], frame[3:9], frame[9:])

        packet = protocol.read_packet(timeout=0.5)

        assert packet["payload"] == bytes(range(11))

    def test_header_split_between_chunks(self, protocol, fake_serial):
        frame = build_frame(PacketType.COMMAND, b"\x01\x02")
        fake_serial.feed_chunks(frame[:1], frame[1:])

        assert protocol.read_packet(timeout=0.5)["raw"] == frame

    def test_incomplete_frame_times_out_with_none(self, protocol, fake_serial):
        fake_serial.feed(build_frame(PacketType.COMMAND, b"\x01\x02")[:-2])

        assert protocol.read_packet(timeout=0.05) is None

    def test_incomplete_frame_completes_on_a_later_call(self, protocol, fake_serial):
        frame = build_frame(PacketType.COMMAND, b"\x01\x02")
        fake_serial.feed(frame[:-2])
        assert protocol.read_packet(timeout=0.05) is None

        fake_serial.feed(frame[-2:])

        assert protocol.read_packet(timeout=0.5)["raw"] == frame

    def test_garbage_before_header_is_skipped(self, protocol, fake_serial):
        frame = build_frame(PacketType.COMMAND, b"\x01\x02")
        fake_serial.feed(b"\x00\x13\xAA\x99junk" + frame)

        assert protocol.read_packet(timeout=0.5)["raw"] == frame

    def test_two_frames_back_to_back_are_both_returned(self, protocol, fake_serial):
        first = build_frame(PacketType.POINT, b"\x01\x02\x03")
        second = build_frame(PacketType.COMMAND, b"\x04\x05")
        fake_serial.feed(first + second)

        assert protocol.read_packet(timeout=0.5)["raw"] == first
        assert protocol.read_packet(timeout=0.5)["raw"] == second
        assert protocol.read_packet(timeout=0.05) is None

    def test_frame_and_start_of_next_one_in_one_chunk(self, protocol, fake_serial):
        first = build_frame(PacketType.POINT, b"\x01\x02\x03")
        second = build_frame(PacketType.COMMAND, b"\x04\x05")
        fake_serial.feed_chunks(first + second[:4], second[4:])

        assert protocol.read_packet(timeout=0.5)["raw"] == first
        assert protocol.read_packet(timeout=0.5)["raw"] == second

    @pytest.mark.parametrize("type_byte", [0x00, 0x09, 0x10, 0xFE])
    def test_unknown_packet_type_returns_none_without_raising(self, protocol, fake_serial, type_byte):
        fake_serial.feed(build_frame(type_byte, b"\x01"))

        assert protocol.read_packet(timeout=0.05) is None

    def test_unknown_type_does_not_block_the_next_frame(self, protocol, fake_serial):
        good = build_frame(PacketType.COMMAND, b"\x01\x02")
        fake_serial.feed(build_frame(0x42, b"\x01") + good)

        assert protocol.read_packet(timeout=0.5)["raw"] == good

    @pytest.mark.parametrize("packet_type", [PacketType.ACK, PacketType.ERROR, PacketType.PING, PacketType.TELEMETRY])
    def test_every_defined_type_is_parsed(self, protocol, fake_serial, packet_type):
        fake_serial.feed(build_frame(packet_type, b"\x01"))

        assert protocol.read_packet(timeout=0.5)["type"] is packet_type

    def test_silence_returns_none_after_the_timeout(self, protocol):
        started = time.monotonic()

        assert protocol.read_packet(timeout=0.05) is None

        assert 0.04 <= time.monotonic() - started < 1.0

    def test_zero_timeout_still_reads_waiting_bytes(self, protocol, fake_serial):
        frame = build_frame(PacketType.PING)
        fake_serial.feed(frame)

        assert protocol.read_packet(timeout=0)["raw"] == frame


class TestParsePacket:

    def test_complete_buffer(self, protocol):
        frame = build_frame(PacketType.POINT, b"\x01\x02\x03")

        assert protocol.parse_packet(b"\x00" + frame + b"\x00")["raw"] == frame

    @pytest.mark.parametrize("buffer", [b"", b"\xAA", b"\xAA\x55\x05", b"no header here"])
    def test_buffers_without_a_complete_frame_return_none(self, protocol, buffer):
        assert protocol.parse_packet(buffer) is None
