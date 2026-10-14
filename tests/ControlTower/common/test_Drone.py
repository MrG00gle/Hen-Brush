from pathlib import Path

import pytest

from ControlTower.common import (
    Animation, Color, Command, Drone, DroneAnimationStatus, DroneStatus, Point,
)

ANIMATION_LENGTH = 4


def make_animation(length: int = ANIMATION_LENGTH, start: Point = Point(1.0, 2.0, 3.0)) -> Animation:
    return Animation(
        timestamps=[i * 100 for i in range(length)],
        flight_path=[start] + [Point(float(i), 0.0, 0.0) for i in range(1, length)] if length else [],
        colors=[Color(i, i, i) for i in range(length)],
        path=Path("drone_0.csv"),
    )


@pytest.fixture
def drone() -> Drone:
    return Drone(id=3, animation=make_animation())


class TestConstruction:

    def test_defaults(self, drone):
        assert drone.id == 3
        assert drone.animation_len == ANIMATION_LENGTH
        assert drone.home_position == Point(1.0, 2.0, 3.0)
        assert drone.position == drone.home_position
        assert drone.reported_position == drone.home_position
        assert drone.position_error == 0
        assert drone.status == DroneStatus.OK
        assert drone.animation_status == DroneAnimationStatus.READY
        assert drone.command == Command.TELEMETRY_REQUEST
        assert drone.battery == -1
        assert drone.animation_step == 0

    def test_empty_animation_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            Drone(id=0, animation=make_animation(length=0))

    def test_repr(self, drone):
        assert repr(drone) == f"Drone(id=3, animation={drone.animation})"


class TestAnimationStep:

    @pytest.mark.parametrize(
        "step, valid",
        [
            (-1, False),
            (0, True),
            (1, True),
            (ANIMATION_LENGTH - 1, True),
            (ANIMATION_LENGTH, False),
            (ANIMATION_LENGTH + 1, False),
        ],
    )
    def test_boundaries(self, drone, step, valid):
        if valid:
            drone.animation_step = step
            assert drone.animation_step == step
        else:
            with pytest.raises(ValueError, match="animation step"):
                drone.animation_step = step

    def test_rejected_value_keeps_previous_step(self, drone):
        drone.animation_step = 2

        with pytest.raises(ValueError):
            drone.animation_step = ANIMATION_LENGTH

        assert drone.animation_step == 2

    def test_single_frame_animation_only_allows_step_zero(self):
        single = Drone(id=0, animation=make_animation(length=1))

        single.animation_step = 0
        with pytest.raises(ValueError):
            single.animation_step = 1


class TestBattery:

    @pytest.mark.parametrize("value", [0, 1, 50, 99, 100])
    def test_valid_values(self, drone, value):
        drone.battery = value

        assert drone.battery == value

    @pytest.mark.parametrize("value", [-1, 101, 1000])
    def test_invalid_values_raise(self, drone, value):
        drone.battery = 40

        with pytest.raises(ValueError, match="battery"):
            drone.battery = value

        assert drone.battery == 40


class TestPositions:

    def test_position_error_is_euclidean_distance_in_3d(self, drone):
        drone.position = Point(0.0, 0.0, 0.0)
        drone.reported_position = Point(3.0, 4.0, 0.0)

        assert drone.position_error == 5.0

    def test_position_error_includes_z(self, drone):
        drone.position = Point(0.0, 0.0, 0.0)
        drone.reported_position = Point(0.0, 3.0, 4.0)

        assert drone.position_error == 5.0

    def test_position_error_follows_later_changes(self, drone):
        drone.position = Point(0.0, 0.0, 0.0)
        drone.reported_position = Point(3.0, 4.0, 0.0)
        assert drone.position_error == 5.0

        drone.reported_position = Point(0.0, 0.0, 2.0)

        assert drone.position_error == 2.0

    def test_setters_store_the_new_points(self, drone):
        drone.position = Point(7, 8, 9)
        drone.reported_position = Point(1, 1, 1)

        assert drone.position == Point(7, 8, 9)
        assert drone.reported_position == Point(1, 1, 1)
        assert drone.home_position == Point(1.0, 2.0, 3.0)


class TestStateSetters:

    def test_status(self, drone):
        drone.status = DroneStatus.LOST

        assert drone.status == DroneStatus.LOST

    def test_animation_status(self, drone):
        drone.animation_status = DroneAnimationStatus.PAUSED

        assert drone.animation_status == DroneAnimationStatus.PAUSED

    def test_command(self, drone):
        drone.command = Command.RTH

        assert drone.command == Command.RTH


class TestFrameAccess:

    def test_get_frame_delegates_to_the_animation(self, drone):
        assert drone.get_frame(1) == drone.animation.get_frame(1)
        assert drone.get_frame(0)[1] == drone.home_position

    @pytest.mark.parametrize("index", [-1, ANIMATION_LENGTH])
    def test_get_frame_out_of_range_returns_none(self, drone, index):
        assert drone.get_frame(index) is None

    def test_get_index_delegates_to_the_animation(self, drone):
        assert drone.get_index(drone.get_frame(2)) == 2

    def test_get_index_of_unknown_frame_returns_none(self, drone):
        assert drone.get_index((12345, Point(0, 0, 0), Color(0, 0, 0))) is None


class TestOrderingAndIdentity:

    def test_equality_is_by_id(self):
        assert Drone(1, make_animation()) == Drone(1, make_animation(length=2))
        assert Drone(1, make_animation()) != Drone(2, make_animation())

    def test_comparison_with_other_types(self, drone):
        assert drone != 3
        assert (drone == "drone") is False
        with pytest.raises(TypeError):
            drone < 3

    def test_less_than_is_by_id(self):
        assert Drone(1, make_animation()) < Drone(2, make_animation())
        assert not Drone(2, make_animation()) < Drone(1, make_animation())
        assert not Drone(2, make_animation()) < Drone(2, make_animation())

    def test_sorting_orders_by_id(self):
        drones = [Drone(i, make_animation()) for i in (5, 1, 3)]

        assert [d.id for d in sorted(drones)] == [1, 3, 5]

    def test_hashable_and_hash_matches_equality(self):
        a, b = Drone(1, make_animation()), Drone(1, make_animation(length=2))

        assert hash(a) == hash(b)
        assert len({a, b, Drone(2, make_animation())}) == 2

    def test_usable_as_dict_key(self):
        drone = Drone(4, make_animation())

        assert {drone: "x"}[Drone(4, make_animation())] == "x"
