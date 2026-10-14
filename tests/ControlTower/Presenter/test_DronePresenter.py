import dataclasses
import threading

import pytest

from ControlTower.Presenter import ActionResult, ButtonStates, DronePresenter, DroneRow
from ControlTower.common import DroneAnimationStatus, DroneStatus, Point
from tests.helpers.stub_controller import StubController

LIVE = DroneAnimationStatus.LIVE
PAUSED = DroneAnimationStatus.PAUSED
ENDED = DroneAnimationStatus.ENDED
READY = DroneAnimationStatus.READY


@pytest.fixture
def stub(make_drones) -> StubController:
    return StubController(make_drones(num_drones=3, anim_length=10))


@pytest.fixture
def presenter(stub) -> DronePresenter:
    return DronePresenter(stub)


class TestDroneRow:
    def make(self, **overrides) -> DroneRow:
        fields = dict(drone_id=1, status="Ok", animation_status="Live", position="1.00, 2.00, 3.00",
                      position_error="0.00", step_text="3/10", step=3, length=10)
        fields.update(overrides)
        return DroneRow(**fields)

    def test_is_frozen(self):
        row = self.make()
        with pytest.raises(dataclasses.FrozenInstanceError):
            row.status = "Lost"

    def test_equality_is_by_value(self):
        assert self.make() == self.make()
        assert self.make() != self.make(step=4)


class TestRows:
    def test_one_row_per_drone_sorted_by_id(self, stub, presenter):
        stub.drones.reverse()
        assert [row.drone_id for row in presenter.rows()] == [0, 1, 2]

    def test_values_are_formatted_once(self, stub, presenter):
        drone = stub.drones[1]
        drone.position = Point(0.0, 0.0, 0.0)
        drone.reported_position = Point(3.0, 4.0, 0.0)
        drone.status = DroneStatus.LOST
        drone.animation_status = PAUSED
        drone.animation_step = 3

        assert presenter.rows()[1] == DroneRow(
            drone_id=1, status="Lost", animation_status="Paused", position="3.00, 4.00, 0.00",
            position_error="5.00", step_text="3/10", step=3, length=10,
        )

    def test_position_is_rounded_to_two_decimals(self, stub, presenter):
        stub.drones[0].reported_position = Point(1.005, -2.3456, 0.1)
        assert presenter.rows()[0].position == "1.00, -2.35, 0.10"

    def test_initial_row(self, presenter):
        row = presenter.rows()[0]
        assert (row.status, row.animation_status, row.step_text) == ("Ok", "Ready", "0/10")

    def test_no_drones(self):
        assert DronePresenter(StubController([])).rows() == []


class TestSelection:
    def test_nothing_selected_initially(self, presenter):
        assert presenter.selected_id is None

    def test_select_known_id(self, presenter):
        assert presenter.select(2) is True
        assert presenter.selected_id == 2

    def test_unknown_id_keeps_previous_selection(self, presenter):
        presenter.select(1)
        assert presenter.select(99) is False
        assert presenter.selected_id == 1

    def test_none_clears_selection(self, presenter):
        presenter.select(1)
        assert presenter.select(None) is True
        assert presenter.selected_id is None


class TestActions:
    @pytest.mark.parametrize("action", ["start", "pause", "stop"])
    def test_selected_action_passes_only_the_selected_drone(self, stub, presenter, action):
        presenter.select(2)
        result = getattr(presenter, f"{action}_selected")()
        assert result.ok is True
        assert stub.calls == [(action, [2])]

    @pytest.mark.parametrize("action", ["start", "pause", "stop"])
    def test_all_action_passes_every_drone(self, stub, presenter, action):
        result = getattr(presenter, f"{action}_all")()
        assert result.ok is True
        assert stub.calls == [(action, [0, 1, 2])]

    @pytest.mark.parametrize("action", ["start", "pause", "stop"])
    def test_selected_action_without_selection_does_nothing(self, stub, presenter, action):
        result = getattr(presenter, f"{action}_selected")()
        assert result == ActionResult(False, "No drone selected")
        assert stub.calls == []

    @pytest.mark.parametrize("action", ["start", "pause", "stop"])
    def test_all_action_without_drones_does_nothing(self, action):
        stub = StubController([])
        result = getattr(DronePresenter(stub), f"{action}_all")()
        assert result.ok is False
        assert stub.calls == []

    @pytest.mark.parametrize("scope", ["selected", "all"])
    def test_controller_exception_becomes_failed_result(self, stub, presenter, scope, caplog):
        presenter.select(0)
        stub.error = RuntimeError("serial gone")

        result = getattr(presenter, f"start_{scope}")()

        assert result.ok is False
        assert "serial gone" in result.message
        assert "serial gone" in caplog.text

    def test_result_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            ActionResult(True, "x").ok = False


class TestButtonStates:
    @pytest.mark.parametrize("state, start, pause, stop", [
        (READY, True, False, False),
        (PAUSED, True, False, True),
        (ENDED, True, False, False),
        (LIVE, False, True, True),
    ])
    def test_selected_buttons_follow_the_state(self, stub, presenter, state, start, pause, stop):
        stub.drones[1].animation_status = state
        presenter.select(1)
        buttons = presenter.button_states()
        assert (buttons.start, buttons.pause, buttons.stop) == (start, pause, stop)

    def test_selected_buttons_off_without_selection(self, presenter):
        buttons = presenter.button_states()
        assert (buttons.start, buttons.pause, buttons.stop) == (False, False, False)

    def test_all_buttons_when_every_drone_is_ready(self, presenter):
        assert presenter.button_states() == ButtonStates(False, False, False, True, False, False)

    def test_all_buttons_when_a_drone_is_live(self, stub, presenter):
        stub.drones[0].animation_status = LIVE
        assert presenter.button_states() == ButtonStates(False, False, False, True, True, True)

    def test_all_buttons_when_every_drone_is_live(self, stub, presenter):
        for drone in stub.drones:
            drone.animation_status = LIVE
        assert presenter.button_states() == ButtonStates(False, False, False, False, True, True)

    def test_no_drones(self):
        assert DronePresenter(StubController([])).button_states() == ButtonStates(False, False, False, False, False, False)

    def test_is_frozen(self, presenter):
        with pytest.raises(dataclasses.FrozenInstanceError):
            presenter.button_states().start = True


def test_rows_survive_concurrent_mutation(stub, presenter):
    errors = []
    stop = threading.Event()

    def hammer():
        step = 0
        while not stop.is_set():
            for drone in stub.drones:
                drone.animation_status = LIVE if step % 2 else PAUSED
                drone.animation_step = step % drone.animation_len
                drone.reported_position = Point(float(step), 1.0, 2.0)
            step += 1

    thread = threading.Thread(target=hammer, daemon=True)
    thread.start()
    try:
        for _ in range(1000):
            rows = presenter.rows()
            presenter.button_states()
            assert len(rows) == 3
            for row in rows:
                assert row.animation_status in ("Live", "Paused", "Ready")
                assert row.step_text == f"{row.step}/{row.length}"
                assert 0 <= row.step < row.length
                assert row.position.count(",") == 2
    except Exception as error:  # surface assertion errors from the loop
        errors.append(error)
    finally:
        stop.set()
        thread.join(timeout=2)

    assert errors == []
