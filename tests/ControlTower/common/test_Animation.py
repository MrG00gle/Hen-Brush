import logging
from pathlib import Path

import pytest

from ControlTower.common import Animation, Color, Point

PATH = Path("drone_7.csv")


@pytest.fixture
def animation() -> Animation:
    return Animation(
        timestamps=[0, 100, 250],
        flight_path=[Point(0, 0, 0), Point(1, 2, 3), Point(4, 5, 6)],
        colors=[Color(1, 2, 3), Color(4, 5, 6), Color(7, 8, 9)],
        path=PATH,
    )


@pytest.fixture
def empty_animation() -> Animation:
    return Animation(timestamps=[], flight_path=[], colors=[], path=PATH)


class TestAnimation:

    def test_attributes(self, animation):
        assert animation.timestamps == [0, 100, 250]
        assert animation.flight_path[1] == Point(1, 2, 3)
        assert animation.colors[2] == Color(7, 8, 9)
        assert animation.path == PATH

    def test_len(self, animation, empty_animation):
        assert len(animation) == 3
        assert len(empty_animation) == 0

    def test_iter_yields_frames_in_order(self, animation):
        assert list(animation) == [
            (0, Point(0, 0, 0), Color(1, 2, 3)),
            (100, Point(1, 2, 3), Color(4, 5, 6)),
            (250, Point(4, 5, 6), Color(7, 8, 9)),
        ]

    def test_reversed_yields_frames_backwards(self, animation):
        assert [frame[0] for frame in reversed(animation)] == [250, 100, 0]

    def test_iter_of_empty_animation(self, empty_animation):
        assert list(empty_animation) == []
        assert list(reversed(empty_animation)) == []

    def test_equality(self, animation):
        other = Animation(list(animation.timestamps), list(animation.flight_path), list(animation.colors), PATH)

        assert animation == other

    def test_repr_shows_first_frame(self, animation):
        assert repr(animation) == f"Animation(timestamp=0, flight_path=0 0 0, color=(R:1, G:2, B:3), path={PATH})"

    def test_repr_of_empty_animation_does_not_raise(self, empty_animation):
        assert repr(empty_animation) == f"Animation(empty, path={PATH})"


class TestGetFrame:

    @pytest.mark.parametrize("index", [0, 1, 2])
    def test_valid_index(self, animation, index):
        assert animation.get_frame(index) == (
            animation.timestamps[index], animation.flight_path[index], animation.colors[index],
        )

    @pytest.mark.parametrize("index", [3, 4, 100])
    def test_index_past_the_end_returns_none(self, animation, index):
        assert animation.get_frame(index) is None

    @pytest.mark.parametrize("index", [-1, -3, -4])
    def test_negative_index_returns_none_instead_of_wrapping(self, animation, index):
        assert animation.get_frame(index) is None

    def test_empty_animation_has_no_frames(self, empty_animation):
        assert empty_animation.get_frame(0) is None

    def test_out_of_range_is_logged(self, animation, caplog):
        with caplog.at_level(logging.ERROR):
            animation.get_frame(10)

        assert "drone_7.csv" in caplog.text


class TestGetIndex:

    @pytest.mark.parametrize("index", [0, 1, 2])
    def test_finds_frame_by_timestamp(self, animation, index):
        assert animation.get_index(animation.get_frame(index)) == index

    def test_missing_frame_returns_none(self, animation, caplog):
        with caplog.at_level(logging.ERROR):
            result = animation.get_index((999, Point(0, 0, 0), Color(0, 0, 0)))

        assert result is None
        assert "not present" in caplog.text

    def test_only_the_timestamp_is_compared(self, animation):
        assert animation.get_index((100, Point(9, 9, 9), Color(9, 9, 9))) == 1
