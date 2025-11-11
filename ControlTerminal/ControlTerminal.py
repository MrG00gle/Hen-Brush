from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Button, DataTable, RichLog, Label
from textual.binding import Binding


# UI Prototype


class DroneControlApp(App):
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.left_width = 50

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)

        # Main content area
        with Horizontal(id="main-content"):
            # Left side: Scrollable list of drones
            with Vertical(id="drones-section"):
                yield Label("Scrollable List of Drones")
                table = DataTable()
                table.add_columns("ID", "Battery %", "Drone Status", "Animation Status", "Checkbox")
                # Add example rows (you can populate dynamically)
                table.add_row("1", "85%", "Idle", "Off", "[ ]")
                table.add_row("2", "92%", "Flying", "On", "[x]")
                yield table

            # Right side: Scrollable logs
            with Vertical(id="logs-section"):
                yield Label("Scrollable Logs")
                yield RichLog(highlight=True, markup=True)

        # Bottom buttons
        with Horizontal(id="buttons"):
            yield Button("Start Button", variant="success")
            yield Button("Stop Button", variant="error")
            yield Button("Pause Button", variant="warning")

        yield Footer()

    def on_mount(self) -> None:
        """Post-mount hook."""
        self.update_sizes()
        # Example: Write something to logs
        logs = self.query_one(RichLog)
        logs.write("Application started.")
        logs.write("Use Ctrl+, to decrease left pane, Ctrl+. to increase.")

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
    app = DroneControlApp()
    app.run()