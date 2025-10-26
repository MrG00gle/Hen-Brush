import pytest
import logging
from ControlTower.common.Point import Point
from ControlTower.common.Color import Color
from ControlTower.common.PointPacket import PointPacket


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')


class TestPointPacket:

    def test_init(self):
        drone_id = 1
        point = Point(x=1.1, y=2.2, z=3.3)
        color = Color(r=100, g=200, b=125)
        pac = PointPacket(drone_id=drone_id, point=point, color=color)
        logging.debug(f"Packet (hex): {pac.packet.hex()}")
        logging.debug(f"Packet length: {len(pac.packet)} bytes")
        return True