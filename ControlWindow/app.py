"""The Adw.Application that owns the main window and shuts the controller down on exit."""

from typing import Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # noqa: E402

from ControlTower.Presenter import DronePresenter, LogBuffer  # noqa: E402

from .window import HenBrushWindow  # noqa: E402

APPLICATION_ID = "org.henbrush.HenBrush"


class HenBrushApplication(Adw.Application):
    """GTK application showing one ``HenBrushWindow``."""

    def __init__(self,
                 presenter: Optional[DronePresenter] = None,
                 log_buffer: Optional[LogBuffer] = None,
                 shutdown: Optional[Callable[[], None]] = None,
                 flags: Gio.ApplicationFlags = Gio.ApplicationFlags.FLAGS_NONE) -> None:
        """Create the application.

        Args:
            presenter: Passed to the window; None shows the skeleton only.
            log_buffer: Passed to the window; None leaves the log view empty.
            shutdown: Called once when the application shuts down, e.g. ``ControlTower.shutdown``.
            flags: Application flags; tests use ``NON_UNIQUE`` so they don't talk to a running instance.
        """
        super().__init__(application_id=APPLICATION_ID, flags=flags)
        self._presenter = presenter
        self._log_buffer = log_buffer
        self._shutdown_hook = shutdown

    def do_activate(self) -> None:
        """Show the window, creating it on the first activation."""
        windows = self.get_windows()
        if windows:
            window = windows[0]
        else:
            window = HenBrushWindow(application=self, presenter=self._presenter, log_buffer=self._log_buffer)
        window.present()

    def do_shutdown(self) -> None:
        """Run the shutdown hook once, then let GTK finish."""
        hook, self._shutdown_hook = self._shutdown_hook, None
        if hook is not None:
            hook()
        Adw.Application.do_shutdown(self)
