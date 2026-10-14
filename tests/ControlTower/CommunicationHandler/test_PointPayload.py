import math
from types import SimpleNamespace

import pytest

from ControlTower.common import Point, Command
from ControlTower.CommunicationHandler.payload import PointPayload
from tests.helpers.decoders import decode_point_payload


class TestPointPayload:

    def test_create_payload(self):
        drone_id = 1
        point = Point(x=1.1, y=2.2, z=3.3)
        pac = PointPayload(drone_id=drone_id, point=point)

        decoded_payload = decode_point_payload(pac.payload)

        assert len(pac.payload) == 8
        assert decoded_payload['drone_id'] == drone_id
        assert decoded_payload['command'] == Command.POSITION.value
        assert decoded_payload['x'] == point.X
        assert decoded_payload['y'] == point.Y
        assert decoded_payload['z'] == point.Z

    def test_properties(self):
        point = Point(1.0, 2.0, 3.0)
        pac = PointPayload(drone_id=4, point=point)

        assert pac.drone_id == 4
        assert pac.point is point
        assert pac.command == Command.POSITION
        assert isinstance(pac.payload, bytes)

    def test_explicit_command_is_used_verbatim(self):
        pac = PointPayload(drone_id=1, point=Point(0, 0, 0), command=Command.RTH)

        assert pac.command == Command.RTH
        assert pac.payload[1] == Command.RTH.value

    @pytest.mark.parametrize("drone_id", [0, 1, 255])
    def test_valid_drone_ids(self, drone_id):
        assert PointPayload(drone_id, Point(0, 0, 0)).payload[0] == drone_id

    @pytest.mark.parametrize("drone_id", [-1, 256, 1000, "1", 1.5, None])
    def test_invalid_drone_ids_raise(self, drone_id):
        with pytest.raises(ValueError, match="Drone ID"):
            PointPayload(drone_id, Point(0, 0, 0))

    def test_wire_encoding_is_little_endian_float16(self):
        pac = PointPayload(1, Point(2.0, 1.0, -2.0))

        assert pac.payload[2:4] == bytes.fromhex("0040")
        assert pac.payload[4:6] == bytes.fromhex("003c")
        assert pac.payload[6:8] == bytes.fromhex("00c0")

    @pytest.mark.parametrize(
        "point, expected",
        [
            (Point(0, 0, 0), (0.0, 0.0, 0.0)),
            (Point(-1.5, -2.0, -0.5), (-1.5, -2.0, -0.5)),
            (Point(65504, -65504, 65504), (65504.0, -65504.0, 65504.0)),
            (Point(1e-10, 0, 0), (0.0, 0.0, 0.0)),
        ],
        ids=["zero", "negative", "float16-max", "underflow-to-zero"],
    )
    def test_coordinates_round_trip_through_float16(self, point, expected):
        decoded = decode_point_payload(PointPayload(1, point).payload)

        assert (decoded['x'], decoded['y'], decoded['z']) == expected

    def test_float16_max_bytes(self):
        assert PointPayload(1, Point(65504, 0, 0)).payload[2:4] == bytes.fromhex("ff7b")

    @pytest.mark.parametrize("value", [-1, 256])
    def test_command_byte_out_of_range_raises(self, value):
        with pytest.raises(ValueError, match="Command"):
            PointPayload(1, Point(0, 0, 0), command=SimpleNamespace(value=value))

    def test_non_numeric_coordinate_raises(self):
        with pytest.raises(ValueError, match="float16"):
            PointPayload(1, Point("abc", 0, 0))

    @pytest.mark.parametrize("bad", [1e6, -1e6, 65520.0, math.inf, -math.inf, math.nan])
    @pytest.mark.parametrize("axis", ["x", "y", "z"])
    def test_coordinates_outside_float16_range_raise(self, axis, bad):
        coordinates = {"x": 0.0, "y": 0.0, "z": 0.0, axis: bad}

        with pytest.raises(ValueError, match="float16"):
            PointPayload(1, Point(**coordinates))
