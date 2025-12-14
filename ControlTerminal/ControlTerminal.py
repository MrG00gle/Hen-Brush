from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Button, DataTable, RichLog, Label
from textual.binding import Binding
from textual.widgets._data_table import CellDoesNotExist

from ControlTower import ControlTower


# UI Prototype


class ControlTerminal(App, ControlTower):
    """A simple TUI for controlling a drone swarm."""

    BINDINGS = [
        Binding("ctrl+comma", "resize_decrease", "Decrease left pane size"),
        Binding("ctrl+period", "resize_increase", "Increase left pane size"),
    ]

    CSS = """
    #main-content {
        height: 1fr;
    }

    #drones-section {
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
    """

    def __init__(self,
                 path_to_animation: str,
                 serial_port: str | None = None,
                 serial_speed: int | None = None,
                 serial_timeout: int | None = None,
                 **kwargs):

        App.__init__(self, **kwargs)

        ControlTower.__init__(self,
            path_to_animation=path_to_animation,
            serial_port=serial_port,
            serial_speed=serial_speed,
            serial_timeout=serial_timeout)

        self.left_width = 70

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)

        # Main content area
        with Horizontal(id="main-content"):
            # Left side: Scrollable list of drones
            with Vertical(id="drone-section"):
                yield Label("Drone List")
                yield DataTable(name="DroneTable", id="drone_table", show_cursor=True, zebra_stripes=True)

            # Right side: Scrollable logs
            with Vertical(id="logs-section"):
                yield Label("Scrollable Logs")
                yield RichLog(highlight=True, markup=True)

        # Bottom buttons
        with Horizontal(id="buttons"):
            yield Button("Start Button", name="Start_Button", id="start-button", variant="success")
            yield Button("Stop Button", name="Stop_Button", id="stop-button", variant="error")
            yield Button("Pause Button", name="Pause_Button", id="pause-button", variant="warning")

        yield Footer()

    def on_mount(self) -> None:
        """Post-mount hook."""
        self.update_sizes()

        # ===== Drone Table =====
        self.create_drone_table()

        # Example: Write something to logs
        logs = self.query_one(RichLog)
        logs.write("Application started.")
        logs.write("Use Ctrl+, to decrease left pane, Ctrl+. to increase.")

    def create_drone_table(self):
        """Creates DroneTable/drone_table and populate rows"""
        drone_table = self.query_one(selector="#drone_table", expect_type=DataTable)
        drone_table.cursor_type = "row"
        drone_table.add_columns("ID", "Drone Status", "Animation Status", "Position", "Pos. error", "Animation Step")

        for drone in self.drones:
            drone_table.add_row(
                f"{self.drones.index(drone)}",
                f"{drone.status.name}",
                f"{drone.animation_status}",
                f"{drone.reported_position}"
                f"{drone.position_error}",
                f"{drone.animation_step}/{drone.animation_len}",
                key=f"{self.drones.index(drone)}"
            )

    def update_drone_table(self):
        """Update DroneTable/drone_table"""
        drone_table = self.query_one(selector="#drone_table", expect_type=DataTable)
        for drone in self.drones:

            value_list = [
                str(self.drones.index(drone)),
                drone.status.name,
                str(drone.animation_status),
                str(drone.reported_position),
                str(drone.position_error),
                str(drone.animation_step)
            ]

            i = 0
            for col in drone_table.columns:
                try:
                    if i == 5:
                        drone_table.update_cell(row_key=str(self.drones.index(drone)), column_key=col, value=f"{value_list[i]}/{drone.animation_len}")
                    else:
                        drone_table.update_cell(row_key=str(self.drones.index(drone)), column_key=col, value=value_list[i])
                    i = + 1
                except CellDoesNotExist:
                    logs = self.query_one(RichLog)
                    logs.write(f"Cell ({self.drones.index(drone)}/{col}) - does not exist!!!")

    def update_sizes(self) -> None:
        """Update the sizes of the panes."""
        self.query_one("#drones-section").styles.width = f"{self.left_width}%"
        self.query_one("#logs-section").styles.width = f"{100 - self.left_width}%"

    def action_resize_decrease(self) -> None:
        """Decrease the left pane width."""
        self.left_width = max(20, self.left_width - 5)
        self.update_sizes()

    def action_resize_increase(self) -> None:
        """Increase the left pane width."""
        self.left_width = min(80, self.left_width + 5)
        self.update_sizes()


if __name__ == "__main__":
    app = ControlTerminal()
    app.run()