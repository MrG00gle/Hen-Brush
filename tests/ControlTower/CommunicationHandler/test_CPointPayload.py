import math
from types import SimpleNamespace

import pytest

from ControlTower.common import Point, Color, Command
from ControlTower.CommunicationHandler.payload import CPointPayload
from tests.helpers.decoders import decode_cpoint_payload


class TestCPointPayload:

    def test_create_payload(self):
        drone_id = 1
        point = Point(x=1.1, y=2.2, z=3.3)
        color = Color(r=100, g=200, b=125)
        pac = CPointPayload(drone_id=drone_id, point=point, color=color)

        decoded_payload = decode_cpoint_payload(pac.payload)

        assert len(pac.payload) == 11
        assert decoded_payload['drone_id'] == drone_id
        assert decoded_payload['command'] == Command.POSITION_COLOR.value
        assert decoded_payload['x'] == point.X
        assert decoded_payload['y'] == point.Y
        assert decoded_payload['z'] == point.Z
        assert decoded_payload['r'] == color.R
        assert decoded_payload['g'] == color.G
        assert decoded_payload['b'] == color.B

    def test_properties(self):
        point, color = Point(1.0, 2.0, 3.0), Color(1, 2, 3)
        pac = CPointPayload(drone_id=4, point=point, color=color)

        assert pac.drone_id == 4
        assert pac.point is point
        assert pac.color is color
        assert pac.command == Command.POSITION_COLOR
        assert isinstance(pac.payload, bytes)

    def test_explicit_command_is_used_verbatim(self):
        pac = CPointPayload(1, Point(0, 0, 0), Color(0, 0, 0), command=Command.POSITION)

        assert pac.command == Command.POSITION
        assert pac.payload[1] == Command.POSITION.value

    @pytest.mark.parametrize("drone_id", [0, 1, 255])
    def test_valid_drone_ids(self, drone_id):
        assert CPointPayload(drone_id, Point(0, 0, 0), Color(0, 0, 0)).payload[0] == drone_id

    @pytest.mark.parametrize("drone_id", [-1, 256, "1", 1.5, None])
    def test_invalid_drone_ids_raise(self, drone_id):
        with pytest.raises(ValueError, match="Drone ID"):
            CPointPayload(drone_id, Point(0, 0, 0), Color(0, 0, 0))

    @pytest.mark.parametrize("value", [0, 128, 255])
    @pytest.mark.parametrize("channel", ["r", "g", "b"])
    def test_valid_color_channels(self, channel, value):
        channels = {"r": 0, "g": 0, "b": 0, channel: value}

        decoded = decode_cpoint_payload(CPointPayload(1, Point(0, 0, 0), Color(**channels)).payload)

        assert decoded[channel] == value

    @pytest.mark.parametrize("value", [-1, 256, 1000, 1.5, 255.0, "255", None])
    @pytest.mark.parametrize("channel", ["r", "g", "b"])
    def test_invalid_color_channels_raise(self, channel, value):
        channels = {"r": 0, "g": 0, "b": 0, channel: value}

        with pytest.raises(ValueError, match="RGB"):
            CPointPayload(1, Point(0, 0, 0), Color(**channels))

    def test_wire_layout(self):
        pac = CPointPayload(9, Point(2.0, 1.0, -2.0), Color(1, 2, 3), command=Command.POSITION_COLOR)

        assert pac.payload == bytes.fromhex("0903" "0040" "003c" "00c0" "010203")

    @pytest.mark.parametrize("value", [-1, 256])
    def test_command_byte_out_of_range_raises(self, value):
        with pytest.raises(ValueError, match="Command"):
            CPointPayload(1, Point(0, 0, 0), Color(0, 0, 0), command=SimpleNamespace(value=value))

    @pytest.mark.parametrize("bad", [1e6, -1e6, math.inf, math.nan])
    @pytest.mark.parametrize("axis", ["x", "y", "z"])
    def test_coordinates_outside_float16_range_raise(self, axis, bad):
        coordinates = {"x": 0.0, "y": 0.0, "z": 0.0, axis: bad}

        with pytest.raises(ValueError, match="float16"):
            CPointPayload(1, Point(**coordinates), Color(0, 0, 0))

    def test_float16_max_is_accepted(self):
        decoded = decode_cpoint_payload(CPointPayload(1, Point(65504, -65504, 0), Color(0, 0, 0)).payload)

        assert (decoded['x'], decoded['y']) == (65504.0, -65504.0)
