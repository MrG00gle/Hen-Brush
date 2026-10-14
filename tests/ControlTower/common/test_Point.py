import pytest

from ControlTower.common.Point import Point


class TestPoint:

    def test_init(self):
        point = Point(x=2.2, y=3.3, z=4.4)
        assert point.X == 2.2
        assert point.Y == 3.3
        assert point.Z == 4.4

    def test_positional_arguments(self):
        point = Point(1, 2, 3)

        assert (point.X, point.Y, point.Z) == (1, 2, 3)

    def test_repr(self):
        assert repr(Point(1.5, -2.0, 0.0)) == "1.5 -2.0 0.0"

    def test_equality(self):
        assert Point(1, 2, 3) == Point(1, 2, 3)
        assert Point(1, 2, 3) != Point(1, 2, 4)
        assert Point(1, 2, 3) != (1, 2, 3)

    @pytest.mark.parametrize("name", ["X", "Y", "Z"])
    def test_coordinates_are_read_only(self, name):
        point = Point(1, 2, 3)

        with pytest.raises(AttributeError):
            setattr(point, name, 9)

    @pytest.mark.parametrize("coordinates", [(0, 0, 0), (-1.5, -2.5, -3.5), (65504, -65504, 1e-3)])
    def test_any_float_is_accepted(self, coordinates):
        point = Point(*coordinates)

        assert (point.X, point.Y, point.Z) == coordinates
