"""GUI tests of the window wired to a presenter. Skipped unless GTK4, libadwaita and a display are available.

A stub controller stands in for the ControlTower, so no serial port or scheduler thread is involved.
"""

import logging
import threading
from typing import List

import pytest

from ControlTower.Presenter import DronePresenter, LogBuffer
from ControlTower.common import Drone, DroneAnimationStatus
from tests.helpers.stub_controller import StubController

pytestmark = pytest.mark.gui

BUTTON_ACTIONS = [
    ("start_button", "start"),
    ("pause_button", "pause"),
    ("stop_button", "stop"),
]
ALL_BUTTON_ACTIONS = [
    ("start_all_button", "start"),
    ("pause_all_button", "pause"),
    ("stop_all_button", "stop"),
]


@pytest.fixture
def drones(make_drones) -> List[Drone]:
    """Two drones with the non-contiguous ids 2 and 5."""
    return [Drone(id=new_id, animation=drone.animation) for new_id, drone in zip((2, 5), make_drones(2, 5))]


@pytest.fixture
def stub(drones) -> StubController:
    return StubController(drones)


@pytest.fixture
def log_buffer():
    buffer = LogBuffer()
    logger = logging.getLogger("henbrush.test.gui")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.addHandler(buffer)
    yield buffer
    logger.removeHandler(buffer)


@pytest.fixture
def window(make_window, stub, log_buffer, monkeypatch):
    _application, win = make_window(DronePresenter(stub), log_buffer)
    toasts = []
    monkeypatch.setattr(win, "show_toast", toasts.append)
    win.toasts = toasts
    return win


def item_at(window, position):
    return window.drone_view.get_model().get_item(position)


def select_row(window, position, pump):
    window.drone_view.get_model().set_selected(position)
    pump()


class TestDroneTable:
    def test_shows_one_row_per_drone(self, window):
        model = window.drone_view.get_model()

        assert model.get_n_items() == 2
        assert [item_at(window, i).drone_id for i in range(2)] == [2, 5]
        assert item_at(window, 0).status == "Ok"
        assert item_at(window, 0).animation_status == "Ready"
        assert item_at(window, 0).step == "0/5"

    def test_has_the_six_columns(self, window):
        titles = [column.get_title() for column in window.drone_view.get_columns()]

        assert titles == ["ID", "Drone Status", "Animation Status", "Position", "Pos. error", "Animation Step"]

    def test_updates_a_cell_in_place_when_the_drone_changes(self, window, drones):
        before = item_at(window, 1)

        drones[1].animation_step = 3
        drones[1].animation_status = DroneAnimationStatus.LIVE
        window._on_tick()

        assert item_at(window, 1) is before
        assert before.step == "3/5"
        assert before.animation_status == "Live"
        assert item_at(window, 0).step == "0/5"

    def test_the_timer_refreshes_without_a_manual_tick(self, window, drones, pump):
        drones[0].animation_step = 4

        assert pump(until=lambda: item_at(window, 0).step == "4/5", timeout=3.0)

    def test_notifies_only_changed_cells(self, window, drones):
        item = item_at(window, 0)
        notified = []
        item.connect("notify::step", lambda *_: notified.append("step"))
        item.connect("notify::status", lambda *_: notified.append("status"))

        drones[0].animation_step = 2
        window._on_tick()

        assert notified == ["step"]

    def test_added_and_removed_drones(self, window, stub, drones, make_drones):
        stub.drones.append(Drone(id=3, animation=make_drones(1, 5)[0].animation))
        window._on_tick()

        assert [item_at(window, i).drone_id for i in range(3)] == [2, 3, 5]

        stub.drones.remove(drones[0])
        window._on_tick()

        assert [item_at(window, i).drone_id for i in range(2)] == [3, 5]
        assert window.drone_view.get_model().get_n_items() == 2

    def test_selecting_a_row_selects_the_drone_in_the_presenter(self, window, pump):
        select_row(window, 1, pump)

        assert window._presenter.selected_id == 5

    def test_refresh_keeps_the_selection(self, window, drones, pump):
        select_row(window, 1, pump)

        drones[0].animation_step = 1
        window._on_tick()

        assert window.drone_view.get_model().get_selected() == 1
        assert window._presenter.selected_id == 5


class TestButtons:
    def test_selected_drone_buttons_are_disabled_without_a_selection(self, window):
        assert not window.start_button.get_sensitive()
        assert not window.pause_button.get_sensitive()
        assert not window.stop_button.get_sensitive()

    def test_all_buttons_follow_the_drone_states(self, window):
        assert window.start_all_button.get_sensitive()
        assert not window.pause_all_button.get_sensitive()
        assert not window.stop_all_button.get_sensitive()

    def test_selection_enables_the_buttons_for_its_state(self, window, drones, pump):
        select_row(window, 0, pump)

        assert window.start_button.get_sensitive()
        assert not window.pause_button.get_sensitive()
        assert not window.stop_button.get_sensitive()

        drones[0].animation_status = DroneAnimationStatus.LIVE
        window._on_tick()

        assert not window.start_button.get_sensitive()
        assert window.pause_button.get_sensitive()
        assert window.stop_button.get_sensitive()
        assert window.pause_all_button.get_sensitive()
        assert window.stop_all_button.get_sensitive()

    @pytest.mark.parametrize("attribute,action", BUTTON_ACTIONS)
    def test_clicking_a_button_calls_the_presenter_for_the_selected_drone(
            self, window, stub, pump, attribute, action):
        select_row(window, 1, pump)

        getattr(window, attribute).emit("clicked")

        assert stub.calls == [(action, [5])]
        assert len(window.toasts) == 1
        assert "drone 5" in window.toasts[0]

    @pytest.mark.parametrize("attribute,action", ALL_BUTTON_ACTIONS)
    def test_clicking_an_all_button_calls_the_presenter_for_every_drone(self, window, stub, attribute, action):
        getattr(window, attribute).emit("clicked")

        assert stub.calls == [(action, [2, 5])]
        assert len(window.toasts) == 1

    @pytest.mark.parametrize("attribute", [name for name, _ in BUTTON_ACTIONS])
    def test_clicking_without_a_selection_calls_nothing_and_says_so(self, window, stub, attribute):
        getattr(window, attribute).emit("clicked")

        assert stub.calls == []
        assert window.toasts == ["No drone selected"]

    def test_a_failing_controller_gives_a_failure_toast(self, window, stub):
        stub.error = RuntimeError("serial port gone")

        window.start_all_button.emit("clicked")

        assert len(window.toasts) == 1
        assert "failed" in window.toasts[0]
        assert "serial port gone" in window.toasts[0]


class TestLogView:
    @staticmethod
    def text(window) -> str:
        buffer = window.log_view.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    def test_backfills_lines_logged_before_the_window_existed(self, make_window, stub):
        buffer = LogBuffer()
        logger = logging.getLogger("henbrush.test.gui.backfill")
        logger.propagate = False
        logger.setLevel(logging.INFO)
        logger.addHandler(buffer)
        logger.info("before the window")

        _application, win = make_window(DronePresenter(stub), buffer)

        assert "before the window" in self.text(win)

    def test_a_line_logged_from_a_worker_thread_appears(self, window, pump):
        worker = threading.Thread(target=logging.getLogger("henbrush.test.gui").warning, args=("from a worker",))
        worker.start()
        worker.join()

        assert pump(until=lambda: "from a worker" in self.text(window))
        assert "WARNING" in self.text(window)

    def test_lines_arrive_in_order(self, window, pump):
        logger = logging.getLogger("henbrush.test.gui")
        for number in range(5):
            logger.info("line %d", number)

        assert pump(until=lambda: "line 4" in self.text(window))
        text = self.text(window)
        assert [text.index(f"line {n}") for n in range(5)] == sorted(text.index(f"line {n}") for n in range(5))

    def test_the_log_is_trimmed_to_the_line_limit(self, window, pump, monkeypatch):
        from ControlWindow import window as window_module

        monkeypatch.setattr(window_module, "MAX_LOG_LINES", 5)
        logger = logging.getLogger("henbrush.test.gui")
        for number in range(12):
            logger.info("trim %d", number)

        assert pump(until=lambda: "trim 11" in self.text(window))
        lines = self.text(window).splitlines()
        assert len(lines) == 5
        assert "trim 11" in lines[-1]
        assert "trim 0" not in self.text(window)


class TestTeardown:
    def test_stopping_updates_removes_the_timer_and_the_subscription(self, window, drones):
        window._stop_updates()
        drones[0].animation_step = 3
        window._on_tick()

        assert window._tick_id is None
        assert item_at(window, 0).step == "0/5"

    def test_stopping_twice_is_harmless(self, window):
        window._stop_updates()
        window._stop_updates()

    def test_closing_the_window_stops_the_updates(self, window):
        window.close()

        assert window._closed
        assert window._tick_id is None
