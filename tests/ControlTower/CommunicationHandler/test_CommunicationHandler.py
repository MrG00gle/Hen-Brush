import logging

import pytest

from ControlTower.common import Point, Color, Command, DroneStatus
from ControlTower.CommunicationHandler import (
    CommandPayload,
    CPointPayload,
    PacketType,
    PointPayload,
    TelemetryPayload,
)
from tests.helpers.decoders import decode_command_payload, decode_cpoint_payload, decode_point_payload
from tests.helpers.frames import build_frame

TELEMETRY_BYTES = bytes([0x0A, 0x40, 0x00, 0xBE, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x80, 0x03, 0x01])


class TestSendRoundTrip:
    """Write with ``send`` and read back from the same ``loop://`` port."""

    def test_point(self, loop_handler):
        payload = PointPayload(12, Point(11, 12, 13))

        loop_handler.send(payload)
        packet = loop_handler.read_packet(timeout=1)

        assert packet["type"] == PacketType.POINT
        assert packet["payload"] == payload.payload
        assert packet["raw"] == build_frame(PacketType.POINT, payload.payload)
        assert decode_point_payload(packet["payload"]) == {
            "drone_id": 12, "command": Command.POSITION.value, "x": 11.0, "y": 12.0, "z": 13.0,
        }

    def test_cpoint(self, loop_handler):
        payload = CPointPayload(12, Point(11, 12, 13), Color(25, 26, 27))

        loop_handler.send(payload)
        packet = loop_handler.read_packet(timeout=1)

        assert packet["type"] == PacketType.CPOINT
        assert packet["payload"] == payload.payload
        assert packet["raw"] == build_frame(PacketType.CPOINT, payload.payload)
        assert decode_cpoint_payload(packet["payload"]) == {
            "drone_id": 12, "command": Command.POSITION_COLOR.value,
            "x": 11.0, "y": 12.0, "z": 13.0, "r": 25, "g": 26, "b": 27,
        }

    def test_command(self, loop_handler):
        payload = CommandPayload(7, Command.ARM)

        loop_handler.send(payload)
        packet = loop_handler.read_packet(timeout=1)

        assert packet["type"] == PacketType.COMMAND
        assert packet["payload"] == payload.payload
        assert packet["raw"] == build_frame(PacketType.COMMAND, payload.payload)
        assert decode_command_payload(packet["payload"]) == (7, Command.ARM.value)

    def test_several_sends_arrive_in_order(self, loop_handler):
        payloads = [CommandPayload(1, Command.ARM), CommandPayload(2, Command.DISARM), CommandPayload(3, Command.RTH)]

        for payload in payloads:
            loop_handler.send(payload)

        received = [loop_handler.read_packet(timeout=1)["payload"] for _ in payloads]
        assert received == [payload.payload for payload in payloads]

    def test_send_writes_the_expected_frame(self, fake_handler, fake_serial):
        fake_handler.send(CommandPayload(7, Command.ARM))

        assert fake_serial.written == [build_frame(PacketType.COMMAND, bytes([7, Command.ARM.value]))]

    def test_unsupported_payload_raises_value_error(self, fake_handler, fake_serial):
        with pytest.raises(ValueError, match="Payload can't be type"):
            fake_handler.send("not a payload")

        assert fake_serial.written == []

    def test_telemetry_payload_cannot_be_sent(self, fake_handler):
        with pytest.raises(ValueError):
            fake_handler.send(TelemetryPayload(TELEMETRY_BYTES))

    def test_send_point_payload_does_not_raise_with_debug_logging(self, fake_handler, caplog):
        caplog.set_level(logging.DEBUG)

        fake_handler.send(PointPayload(1, Point(1, 2, 3)))

        assert "Sending" in caplog.text


class TestListen:

    def test_yields_decoded_telemetry(self, fake_handler, fake_serial):
        fake_serial.feed(build_frame(PacketType.TELEMETRY, TELEMETRY_BYTES))
        listener = fake_handler.listen()

        telemetry = next(listener)

        assert isinstance(telemetry, TelemetryPayload)
        assert telemetry.drone_id == 10
        assert telemetry.point == Point(2.0, -1.5, 0.0)
        assert telemetry.color == Color(255, 0, 128)
        assert telemetry.drone_status == DroneStatus.OK

    def test_yields_none_on_silence(self, fake_handler):
        listener = fake_handler.listen()

        assert next(listener) is None
        assert next(listener) is None

    def test_none_then_telemetry_when_data_arrives_later(self, fake_handler, fake_serial):
        listener = fake_handler.listen()
        assert next(listener) is None

        fake_serial.feed(build_frame(PacketType.TELEMETRY, TELEMETRY_BYTES))

        assert isinstance(next(listener), TelemetryPayload)

    def test_skips_packets_that_are_not_telemetry(self, fake_handler, fake_serial):
        fake_serial.feed(build_frame(PacketType.PONG) + build_frame(PacketType.TELEMETRY, TELEMETRY_BYTES))
        listener = fake_handler.listen()

        assert isinstance(next(listener), TelemetryPayload)

    @pytest.mark.parametrize(
        "bad_payload",
        [
            TELEMETRY_BYTES[:5],
            TELEMETRY_BYTES + b"\x00",
            TELEMETRY_BYTES[:10] + b"\x09" + TELEMETRY_BYTES[11:],
        ],
        ids=["too-short", "too-long", "unknown-status"],
    )
    def test_survives_malformed_telemetry(self, fake_handler, fake_serial, bad_payload):
        fake_serial.feed(build_frame(PacketType.TELEMETRY, bad_payload))
        fake_serial.feed(build_frame(PacketType.TELEMETRY, TELEMETRY_BYTES))
        listener = fake_handler.listen()

        results = [next(listener), next(listener)]

        assert results[0] is None
        assert isinstance(results[1], TelemetryPayload)

    def test_stops_when_the_port_is_closed(self, fake_handler):
        listener = fake_handler.listen()
        assert next(listener) is None

        fake_handler.close()

        assert list(listener) == []


class TestPayloadRepr:

    @pytest.mark.parametrize(
        "payload, name",
        [
            (PointPayload(1, Point(1, 2, 3)), "PointPayload"),
            (CPointPayload(1, Point(1, 2, 3), Color(4, 5, 6)), "CPointPayload"),
            (CommandPayload(1, Command.ARM), "CommandPayload"),
            (TelemetryPayload(TELEMETRY_BYTES), "TelemetryPayload"),
        ],
    )
    def test_repr_works_and_names_the_class(self, payload, name):
        assert repr(payload).startswith(f"{name}(")
        assert f": {payload.drone_id}," in repr(payload)
