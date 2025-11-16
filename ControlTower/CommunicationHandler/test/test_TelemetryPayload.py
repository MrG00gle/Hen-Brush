import logging
from ..payload.TelemetryPayload import TelemetryPayload
from ControlTower.common import Point, Color, DroneStatus


class TestTelemetryPayload:

    def test_init(self):
        packet_bytes = bytes([
            0x0A,  # drone_id = 10
            0x40, 0x00,  # x = 2.0
            0xBE, 0x00,  # y = -1.5
            0x00, 0x00,  # z = 0.0
            0xFF, 0x00, 0x80,  # r=255, g=0, b=128
            0x03,  # drone_status = 3
            0x01  # drone_animation_status = 1
        ])

        telemetry_packet = TelemetryPayload(payload=packet_bytes)
        logging.debug(telemetry_packet)
        assert telemetry_packet.drone_id == 10
        assert telemetry_packet.point == Point(2.0, -1.5, 0.0)
        assert telemetry_packet.color == Color(255, 0, 128)
        assert telemetry_packet.drone_status == DroneStatus.OK

