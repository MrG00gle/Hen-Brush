import pytest

from ControlTower.CommunicationHandler.payload import TelemetryPayload
from ControlTower.common import Point, Color, DroneStatus

SAMPLE = bytes([
    0x0A,  # drone_id = 10
    0x40, 0x00,  # x = 2.0
    0xBE, 0x00,  # y = -1.5
    0x00, 0x00,  # z = 0.0
    0xFF, 0x00, 0x80,  # r=255, g=0, b=128
    0x03,  # drone_status = 3
    0x01,  # byte 11: animation status, not decoded (see TelemetryPayload docstring)
])


class TestTelemetryPayload:

    def test_init(self):
        telemetry_packet = TelemetryPayload(payload=SAMPLE)

        assert telemetry_packet.drone_id == 10
        assert telemetry_packet.point == Point(2.0, -1.5, 0.0)
        assert telemetry_packet.color == Color(255, 0, 128)
        assert telemetry_packet.drone_status == DroneStatus.OK
        assert telemetry_packet.payload == SAMPLE

    @pytest.mark.parametrize("length", [0, 1, 11, 13, 20])
    def test_wrong_length_raises(self, length):
        with pytest.raises(ValueError, match="12 bytes"):
            TelemetryPayload(payload=bytes(length))

    @pytest.mark.parametrize("status", [0, 4, 9, 255])
    def test_unknown_drone_status_raises(self, status):
        payload = SAMPLE[:10] + bytes([status]) + SAMPLE[11:]

        with pytest.raises(ValueError):
            TelemetryPayload(payload=payload)

    @pytest.mark.parametrize("status, expected", [(1, DroneStatus.LOST), (2, DroneStatus.INACTIVE), (3, DroneStatus.OK)])
    def test_every_drone_status(self, status, expected):
        payload = SAMPLE[:10] + bytes([status]) + SAMPLE[11:]

        assert TelemetryPayload(payload=payload).drone_status == expected

    @pytest.mark.parametrize("drone_id", [0, 255])
    def test_drone_id_bounds(self, drone_id):
        assert TelemetryPayload(bytes([drone_id]) + SAMPLE[1:]).drone_id == drone_id

    def test_coordinates_are_decoded_big_endian(self):
        # If the dtype ever changes to little-endian, 40 00 would decode as ~3.8e-6 instead of 2.0.
        assert TelemetryPayload(SAMPLE).point.X == 2.0
        swapped = SAMPLE[:1] + bytes([0x00, 0x40]) + SAMPLE[3:]
        assert TelemetryPayload(swapped).point.X != 2.0

    def test_float16_extremes(self):
        payload = SAMPLE[:1] + bytes([0x7B, 0xFF, 0xFB, 0xFF, 0x00, 0x00]) + SAMPLE[7:]

        point = TelemetryPayload(payload).point

        assert (point.X, point.Y, point.Z) == (65504.0, -65504.0, 0.0)

    def test_twelfth_byte_is_ignored(self):
        changed = SAMPLE[:11] + b"\x04"

        first, second = TelemetryPayload(SAMPLE), TelemetryPayload(changed)

        assert (first.drone_id, first.point, first.color, first.drone_status) == \
               (second.drone_id, second.point, second.color, second.drone_status)

    def test_repr(self):
        text = repr(TelemetryPayload(SAMPLE))

        assert text.startswith("TelemetryPayload(Id: 10,")
