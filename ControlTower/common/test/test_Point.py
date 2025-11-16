import pytest
import logging
from ControlTower.common.Point import Point


class TestPoint:

    def test_init(self):
        point = Point(x=2.2, y=3.3, z=4.4)
        assert point.X == 2.2
        assert point.Y == 3.3
        assert point.Z == 4.4