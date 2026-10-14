"""Skips ``@pytest.mark.gui`` tests unless GTK4, libadwaita, blueprint-compiler and a display are available."""

import shutil
from pathlib import Path
from typing import Optional

import pytest

from ControlWindow.ui_build import compiler_command, is_stale

WINDOW_DIR = Path(__file__).resolve().parent
UI_DIR = Path(__file__).resolve().parents[2] / "ControlWindow" / "ui"

_reason_cache: Optional[str] = None
_reason_computed = False


def gui_unavailable_reason() -> Optional[str]:
    """Why GUI tests can't run here, or None if they can. Computed once."""
    global _reason_cache, _reason_computed
    if _reason_computed:
        return _reason_cache
    _reason_cache = _compute_reason()
    _reason_computed = True
    return _reason_cache


def _compute_reason() -> Optional[str]:
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gdk, Gtk  # noqa: F401
    except (ImportError, ValueError) as error:
        return f"GTK4/libadwaita not available: {error}"

    if is_stale(UI_DIR / "window.blp", UI_DIR / "window.ui") and shutil.which(compiler_command()) is None:
        return f"window.ui is out of date and '{compiler_command()}' is not on PATH"

    try:
        usable = Gtk.init_check()
    except Exception as error:  # pragma: no cover - depends on the GTK build
        return f"GTK could not be initialised: {error}"
    if not usable or Gdk.Display.get_default() is None:
        return "no display available (set DISPLAY/WAYLAND_DISPLAY or run under xvfb-run)"
    return None


@pytest.fixture
def pump():
    """Return ``pump(until=None, timeout=2.0)``: run pending main-loop work, optionally until ``until()`` is true.

    Without ``until`` it only drains what is pending (no sleeping). With ``until`` it keeps iterating
    until the condition holds and returns whether it did, giving up after ``timeout`` seconds.
    """
    import time
    from gi.repository import GLib

    def run(until=None, timeout: float = 2.0) -> bool:
        context = GLib.MainContext.default()
        deadline = time.monotonic() + timeout
        while True:
            while context.pending():
                context.iteration(False)
            if until is None or until():
                return True
            if time.monotonic() > deadline:
                return False
            time.sleep(0.005)

    return run


@pytest.fixture
def make_window():
    """Return ``make_window(presenter=None, log_buffer=None) -> (application, window)``; cleans up afterwards."""
    from gi.repository import Gio

    from ControlWindow.app import HenBrushApplication

    applications = []

    def factory(presenter=None, log_buffer=None):
        application = HenBrushApplication(presenter, log_buffer, flags=Gio.ApplicationFlags.NON_UNIQUE)
        application.register(None)
        application.activate()
        applications.append(application)
        return application, application.get_windows()[0]

    yield factory

    for application in applications:
        for window in application.get_windows():
            window.destroy()


def pytest_collection_modifyitems(config, items):
    """Add a skip marker to every gui test below ``tests/ControlWindow`` when GTK can't be used."""
    gui_items = [
        item for item in items
        if item.get_closest_marker("gui") is not None and WINDOW_DIR in Path(str(item.path)).resolve().parents
    ]
    if not gui_items:
        return
    reason = gui_unavailable_reason()
    if reason is None:
        return
    skip = pytest.mark.skip(reason=reason)
    for item in gui_items:
        item.add_marker(skip)
