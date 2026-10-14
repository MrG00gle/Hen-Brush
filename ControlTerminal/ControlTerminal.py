"""Textual application showing the drone table, action buttons and the log pane."""
from typing import Callable, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Button, DataTable, Footer, Header, Label, RichLog
from textual.widgets.data_table import RowKey

from ControlTower.Presenter import ActionResult, DronePresenter, DroneRow, LogBuffer

COLUMNS = (
    ("id", "ID"),
    ("status", "Drone Status"),
    ("animation_status", "Animation Status"),
    ("position", "Position"),
    ("position_error", "Pos. error"),
    ("step", "Animation Step"),
)
COLUMN_KEYS = tuple(key for key, _ in COLUMNS)

MIN_LEFT_WIDTH = 20
MAX_LEFT_WIDTH = 80
WIDTH_STEP = 5


def row_values(row: DroneRow) -> tuple:
    """Cell values of a presenter row, in ``COLUMN_KEYS`` order."""
    return (
        str(row.drone_id),
        row.status,
        row.animation_status,
        row.position,
        row.position_error,
        row.step_text,
    )


class ControlTerminal(App):
    """A TUI for controlling a drone swarm. It renders a ``DronePresenter`` and a ``LogBuffer``.

    The tables and the log pane are refreshed by polling on a timer (``set_interval``), so scheduler
    and logging threads never touch widgets.
    """

    BINDINGS = [
        Binding("ctrl+comma", "resize_decrease", "Decrease left pane size"),
        Binding("ctrl+period", "resize_increase", "Increase left pane size"),
    ]

    CSS = """
    #main-content {
        height: 1fr;
    }

    #drone-section {
        height: 100%;
    }

    #logs-section {
        height: 100%;
    }

    DataTable {
        height: 1fr;
    }

    RichLog {
        height: 1fr;
    }

    #buttons {
        content-align: center middle;
        height: auto;
    }

    #buttons Button {
        min-width: 12;
    }
    """

    def __init__(self,
                 presenter: DronePresenter,
                 log_buffer: LogBuffer,
                 refresh_interval: float = 0.25,
                 shutdown: Optional[Callable[[], None]] = None,
                 **kwargs):
        """Create the app.

        Args:
            presenter: Supplies the rows and button states, and runs the start/pause/stop actions.
            log_buffer: Source of the lines shown in the log pane.
            refresh_interval: Seconds between refreshes of the table, buttons and log pane.
            shutdown: Called once when the app unmounts, e.g. to stop the controller.
            **kwargs: Passed to ``App``.
        """
        super().__init__(**kwargs)
        self.presenter = presenter
        self.log_buffer = log_buffer
        self.refresh_interval = refresh_interval
        self._shutdown_hook = shutdown
        self._log_cursor = 0
        self.left_width = 70

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)

        with Horizontal(id="main-content"):
            # Left side: the drones
            with Vertical(id="drone-section"):
                yield Label("Drone List")
                yield DataTable(name="DroneTable", id="drone_table", show_cursor=True, zebra_stripes=True)

            # Right side: scrollable logs
            with Vertical(id="logs-section"):
                yield Label("Scrollable Logs")
                yield RichLog(highlight=True, markup=False)

        with Horizontal(id="buttons"):
            yield Button("Start", name="Start_Button", id="start-button", variant="success")
            yield Button("Pause", name="Pause_Button", id="pause-button", variant="warning")
            yield Button("Stop", name="Stop_Button", id="stop-button", variant="error")
            yield Button("Start all", name="Start_All_Button", id="start-all-button", variant="success")
            yield Button("Pause all", name="Pause_All_Button", id="pause-all-button", variant="warning")
            yield Button("Stop all", name="Stop_All_Button", id="stop-all-button", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Fill the panes and start the refresh timer."""
        self.update_sizes()

        table = self.query_one("#drone_table", DataTable)
        table.cursor_type = "row"
        for key, label in COLUMNS:
            table.add_column(label, key=key)

        self._write_log("Application started.")
        self._write_log("Use Ctrl+, to decrease left pane, Ctrl+. to increase.")

        self._refresh()
        self.set_interval(self.refresh_interval, self._refresh)

    def on_unmount(self) -> None:
        """Run the shutdown hook, once."""
        hook, self._shutdown_hook = self._shutdown_hook, None
        if hook is not None:
            hook()

    # --- refresh -----------------------------------------------------------------------------

    def _refresh(self) -> None:
        """Bring the table, the buttons and the log pane up to date."""
        try:
            self.update_drone_table()
            self.update_buttons()
            self.update_log()
        except NoMatches:
            # A tick that fires while the screen is being torn down; nothing left to update.
            pass

    def update_drone_table(self) -> None:
        """Update DroneTable/drone_table from the presenter, adding rows for drones not shown yet."""
        table = self.query_one("#drone_table", DataTable)
        for row in self.presenter.rows():
            values = row_values(row)
            row_key = str(row.drone_id)
            if RowKey(row_key) not in table.rows:
                table.add_row(*values, key=row_key)
                continue
            for column_key, value in zip(COLUMN_KEYS, values):
                table.update_cell(row_key, column_key, value, update_width=True)

    def update_buttons(self) -> None:
        """Enable the buttons that make sense for the current drone states."""
        states = self.presenter.button_states()
        for button_id, enabled in (
                ("start-button", states.start),
                ("pause-button", states.pause),
                ("stop-button", states.stop),
                ("start-all-button", states.start_all),
                ("pause-all-button", states.pause_all),
                ("stop-all-button", states.stop_all),
        ):
            self.query_one(f"#{button_id}", Button).disabled = not enabled

    def update_log(self) -> None:
        """Append the log lines that arrived since the last refresh."""
        entries, self._log_cursor = self.log_buffer.read_since(self._log_cursor)
        for entry in entries:
            self._write_log(f"{entry.level:<8} {entry.message}")

    def _write_log(self, text: str) -> None:
        self.query_one(RichLog).write(text)

    # --- selection and buttons ---------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Select the highlighted drone in the presenter."""
        if event.row_key.value is None:
            return
        self.presenter.select(int(event.row_key.value))
        self.update_buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Run the presenter action behind a button and show its outcome in the log pane."""
        actions = {
            "start-button": self.presenter.start_selected,
            "pause-button": self.presenter.pause_selected,
            "stop-button": self.presenter.stop_selected,
            "start-all-button": self.presenter.start_all,
            "pause-all-button": self.presenter.pause_all,
            "stop-all-button": self.presenter.stop_all,
        }
        action = actions.get(event.button.id)
        if action is None:
            return
        result: ActionResult = action()
        self._write_log(result.message)
        self._refresh()

    # --- pane sizes --------------------------------------------------------------------------

    def update_sizes(self) -> None:
        """Update the sizes of the panes."""
        self.query_one("#drone-section").styles.width = f"{self.left_width}%"
        self.query_one("#logs-section").styles.width = f"{100 - self.left_width}%"

    def action_resize_decrease(self) -> None:
        """Decrease the left pane width."""
        self.left_width = max(MIN_LEFT_WIDTH, self.left_width - WIDTH_STEP)
        self.update_sizes()

    def action_resize_increase(self) -> None:
        """Increase the left pane width."""
        self.left_width = min(MAX_LEFT_WIDTH, self.left_width + WIDTH_STEP)
        self.update_sizes()
