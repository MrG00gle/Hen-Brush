from ControlTower.common import Point, Color, Command
from .utils import decode_point_payload
from ..payload.PointPayload import PointPayload


class TestPointPayload:

    def test_create_payload(self):
        drone_id = 1
        point = Point(x=1.1, y=2.2, z=3.3)
        color = Color(r=100, g=200, b=125)
        pac = PointPayload(drone_id=drone_id, point=point, color=color)

        decoded_payload = decode_point_payload(pac.payload)

        assert len(pac.payload) == 11
        assert decoded_payload['drone_id'] == drone_id
        assert decoded_payload['command'] == Command.POSITION_COLOR.value
        assert decoded_payload['x'] == point.X
        assert decoded_payload['y'] == point.Y
        assert decoded_payload['z'] == point.Z
        assert decoded_payload['r'] == color.R
        assert decoded_payload['g'] == color.G
        assert decoded_payload['b'] == color.B
