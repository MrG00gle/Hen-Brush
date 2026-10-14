import pytest

from ControlTower.common import Color


class TestColor:

    def test_attributes(self):
        color = Color(10, 20, 30)

        assert (color.R, color.G, color.B) == (10, 20, 30)

    def test_keyword_arguments(self):
        color = Color(r=1, g=2, b=3)

        assert (color.R, color.G, color.B) == (1, 2, 3)

    def test_repr(self):
        assert repr(Color(255, 0, 128)) == "(R:255, G:0, B:128)"

    def test_equality(self):
        assert Color(1, 2, 3) == Color(1, 2, 3)
        assert Color(1, 2, 3) != Color(1, 2, 4)
        assert Color(1, 2, 3) != (1, 2, 3)

    @pytest.mark.parametrize("channel", ["R", "G", "B"])
    def test_channels_can_be_changed(self, channel):
        color = Color(0, 0, 0)

        setattr(color, channel, 99)

        assert getattr(color, channel) == 99
