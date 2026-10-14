"""Pilot tests for the Textual UI. Sync tests run each scenario with ``asyncio.run`` (no pytest-asyncio)."""

import asyncio
import logging
from typing import Awaitable, Callable, List

import pytest
from textual.widgets import Button, DataTable, RichLog

from ControlTerminal import ControlTerminal
from ControlTower.Presenter import DronePresenter, LogBuffer
from ControlTower.common import Drone, DroneAnimationStatus, DroneStatus, Point
from tests.helpers.stub_controller import StubController

REFRESH = 0.02
SIZE = (140, 40)
COLUMN_LABELS = ["ID", "Drone Status", "Animation Status", "Position", "Pos. error", "Animation Step"]


@pytest.fixture
def drones(make_drones) -> List[Drone]:
    """Two drones with the non-contiguous ids 2 and 5, so row keys can't be mistaken for list indices."""
    return [Drone(id=new_id, animation=drone.animation) for new_id, drone in zip((2, 5), make_drones(2, 10))]


@pytest.fixture
def stub(drones) -> StubController:
    return StubController(drones)


@pytest.fixture
def log_buffer():
    buffer = LogBuffer()
    buffer.install()
    yield buffer
    buffer.uninstall()


@pytest.fixture
def make_app(stub, log_buffer) -> Callable[..., ControlTerminal]:
    def factory(**kwargs) -> ControlTerminal:
        return ControlTerminal(DronePresenter(stub), log_buffer, refresh_interval=REFRESH, **kwargs)

    return factory


def run_scenario(app: ControlTerminal, scenario: Callable[..., Awaitable[None]]) -> None:
    async def runner() -> None:
        async with app.run_test(size=SIZE) as pilot:
            await scenario(pilot)

    asyncio.run(runner())


def cells(app: ControlTerminal, drone_id: int) -> List[str]:
    table = app.query_one("#drone_table", DataTable)
    return [str(value) for value in table.get_row(str(drone_id))]


def log_text(app: ControlTerminal) -> str:
    return "\n".join(line.text for line in app.query_one(RichLog).lines)


async def tick(pilot) -> None:
    """Wait for a few refresh intervals."""
    await pilot.pause(REFRESH * 5)


class TestTable:
    def test_has_the_six_columns_and_one_six_cell_row_per_drone(self, make_app):
        app = make_app()

        async def scenario(pilot):
            table = app.query_one("#drone_table", DataTable)
            assert [str(column.label) for column in table.columns.values()] == COLUMN_LABELS
            assert table.row_count == 2
            assert all(len(table.get_row(str(drone_id))) == 6 for drone_id in (2, 5))

        run_scenario(app, scenario)

    def test_row_keys_are_drone_ids_not_list_indices(self, make_app):
        app = make_app()

        async def scenario(pilot):
            table = app.query_one("#drone_table", DataTable)
            assert [key.value for key in table.rows] == ["2", "5"]
            assert cells(app, 5)[0] == "5"

        run_scenario(app, scenario)

    def test_initial_cells_are_formatted_by_the_presenter(self, make_app, drones):
        app = make_app()

        async def scenario(pilot):
            assert cells(app, 2) == ["2", "Ok", "Ready", drones_position(drones[0]), "0.00", "0/10"]

        run_scenario(app, scenario)

    def test_every_refresh_updates_all_six_columns(self, make_app, drones):
        app = make_app()

        async def scenario(pilot):
            drone = drones[1]
            drone.status = DroneStatus.LOST
            drone.animation_status = DroneAnimationStatus.LIVE
            drone.reported_position = Point(1.0, 2.0, 3.0)
            drone.animation_step = 4
            await tick(pilot)

            values = cells(app, 5)
            assert values[0] == "5"
            assert values[1] == "Lost"
            assert values[2] == "Live"
            assert values[3] == "1.00, 2.00, 3.00"
            assert values[4] == f"{drone.position_error:.2f}"
            assert values[5] == "4/10"
            assert cells(app, 2)[2] == "Ready"

        run_scenario(app, scenario)

    def test_no_pane_lookup_error_on_mount_and_panes_exist(self, make_app):
        app = make_app()

        async def scenario(pilot):
            assert app.query_one("#drone-section")
            assert app.query_one("#logs-section")

        run_scenario(app, scenario)


def drones_position(drone: Drone) -> str:
    point = drone.reported_position
    return f"{point.X:.2f}, {point.Y:.2f}, {point.Z:.2f}"


class TestButtons:
    def test_all_buttons_are_disabled_when_there_are_no_drones(self, make_app, stub):
        stub.drones.clear()
        app = make_app()

        async def scenario(pilot):
            await tick(pilot)
            for button_id in ("start", "pause", "stop", "start-all", "pause-all", "stop-all"):
                assert app.query_one(f"#{button_id}-button", Button).disabled

        run_scenario(app, scenario)

    def test_the_cursor_row_is_selected_from_the_start(self, make_app, stub):
        app = make_app()

        async def scenario(pilot):
            await tick(pilot)
            assert app.presenter.selected_id == 2
            assert not app.query_one("#start-button", Button).disabled
            assert app.query_one("#pause-button", Button).disabled
            assert app.query_one("#stop-button", Button).disabled
            assert not app.query_one("#start-all-button", Button).disabled

        run_scenario(app, scenario)

    @pytest.mark.parametrize("button_id, action, status", [
        ("start-button", "start", DroneAnimationStatus.READY),
        ("pause-button", "pause", DroneAnimationStatus.LIVE),
        ("stop-button", "stop", DroneAnimationStatus.LIVE),
    ])
    def test_selected_button_calls_the_presenter_for_the_selected_drone(self, make_app, stub, drones, button_id, action, status):
        app = make_app()

        async def scenario(pilot):
            app.query_one("#drone_table", DataTable).move_cursor(row=1)
            drones[1].animation_status = status
            await tick(pilot)

            await pilot.click(f"#{button_id}")
            await tick(pilot)

            assert stub.calls == [(action, [5])]
            assert f"{action.capitalize()} requested for drone 5" in log_text(app)

        run_scenario(app, scenario)

    @pytest.mark.parametrize("button_id, action, status", [
        ("start-all-button", "start", DroneAnimationStatus.READY),
        ("pause-all-button", "pause", DroneAnimationStatus.LIVE),
        ("stop-all-button", "stop", DroneAnimationStatus.LIVE),
    ])
    def test_all_buttons_call_the_presenter_for_every_drone(self, make_app, stub, drones, button_id, action, status):
        app = make_app()

        async def scenario(pilot):
            drones[0].animation_status = status
            await tick(pilot)

            await pilot.click(f"#{button_id}")
            await tick(pilot)

            assert stub.calls == [(action, [2, 5])]

        run_scenario(app, scenario)

    def test_button_states_follow_the_selected_drone(self, make_app, drones):
        app = make_app()

        async def scenario(pilot):
            app.query_one("#drone_table", DataTable).move_cursor(row=0)
            await tick(pilot)
            assert not app.query_one("#start-button", Button).disabled
            assert app.query_one("#pause-button", Button).disabled
            assert app.query_one("#stop-button", Button).disabled

            drones[0].animation_status = DroneAnimationStatus.LIVE
            await tick(pilot)
            assert app.query_one("#start-button", Button).disabled
            assert not app.query_one("#pause-button", Button).disabled
            assert not app.query_one("#stop-button", Button).disabled

        run_scenario(app, scenario)

    def test_arrow_keys_move_the_selection(self, make_app, stub):
        app = make_app()

        async def scenario(pilot):
            app.query_one("#drone_table", DataTable).focus()
            await pilot.press("down")
            await tick(pilot)

            await pilot.click("#start-button")
            await tick(pilot)

            assert stub.calls == [("start", [5])]

        run_scenario(app, scenario)

    def test_controller_failure_is_shown_in_the_log_pane(self, make_app, stub):
        app = make_app()

        async def scenario(pilot):
            stub.error = RuntimeError("serial gone")
            await tick(pilot)

            await pilot.click("#start-all-button")
            await tick(pilot)

            assert "Start failed for all drones (2): serial gone" in log_text(app)

        run_scenario(app, scenario)


class TestLogPane:
    def test_log_records_appear_after_a_refresh(self, make_app):
        app = make_app()

        async def scenario(pilot):
            logging.getLogger().info("hello from the test")
            await tick(pilot)

            assert "hello from the test" in log_text(app)

        run_scenario(app, scenario)

    def test_each_record_is_written_once(self, make_app):
        app = make_app()

        async def scenario(pilot):
            logging.getLogger().info("only once")
            await tick(pilot)
            await tick(pilot)

            assert log_text(app).count("only once") == 1

        run_scenario(app, scenario)

    def test_markup_in_a_message_is_shown_literally(self, make_app):
        app = make_app()

        async def scenario(pilot):
            logging.getLogger().info("odd [/bold] text")
            await tick(pilot)

            assert "odd [/bold] text" in log_text(app)

        run_scenario(app, scenario)


class TestResize:
    @staticmethod
    def widths(app: ControlTerminal):
        return (app.query_one("#drone-section").styles.width.value,
                app.query_one("#logs-section").styles.width.value)

    def test_initial_split(self, make_app):
        app = make_app()

        async def scenario(pilot):
            assert self.widths(app) == (70, 30)

        run_scenario(app, scenario)

    def test_ctrl_comma_and_ctrl_period_resize_the_panes(self, make_app):
        app = make_app()

        async def scenario(pilot):
            await pilot.press("ctrl+comma")
            assert self.widths(app) == (65, 35)
            await pilot.press("ctrl+period", "ctrl+period")
            assert self.widths(app) == (75, 25)

        run_scenario(app, scenario)

    def test_left_pane_stays_between_20_and_80_percent(self, make_app):
        app = make_app()

        async def scenario(pilot):
            for _ in range(15):
                await pilot.press("ctrl+comma")
            assert self.widths(app) == (20, 80)
            for _ in range(20):
                await pilot.press("ctrl+period")
            assert self.widths(app) == (80, 20)

        run_scenario(app, scenario)


class TestWithRealControlTower:
    def test_start_all_and_stop_all_drive_the_scheduler(self, animation_dir, log_buffer):
        from ControlTower import ControlTower

        tower = ControlTower(str(animation_dir(n_drones=2, frames=5)), "loop://", 115200, 0.05)
        app = ControlTerminal(DronePresenter(tower), log_buffer, refresh_interval=REFRESH, shutdown=tower.shutdown)

        async def scenario(pilot):
            await pilot.click("#start-all-button")
            await pilot.pause(0.5)
            assert cells(app, 0)[2] == "Live"
            assert cells(app, 1)[2] == "Live"

            await pilot.click("#stop-all-button")
            await pilot.pause(0.5)
            assert cells(app, 0)[2] != "Live"

        run_scenario(app, scenario)


class TestShutdown:
    def test_shutdown_hook_runs_once_on_exit(self, make_app):
        calls = []
        app = make_app(shutdown=lambda: calls.append("shutdown"))

        async def scenario(pilot):
            assert calls == []

        run_scenario(app, scenario)

        assert calls == ["shutdown"]
