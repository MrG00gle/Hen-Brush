"""GUI smoke test of the window skeleton. Skipped unless GTK4, libadwaita and a display are available."""

import pytest

pytestmark = pytest.mark.gui


def test_window_instantiates_and_template_children_resolve(make_window):
    from gi.repository import Adw, Gtk

    _application, window = make_window()

    assert isinstance(window, Adw.ApplicationWindow)
    assert window.get_title() == "Hen Brush"
    assert isinstance(window.toast_overlay, Adw.ToastOverlay)
    assert isinstance(window.stack, Adw.ViewStack)
    assert isinstance(window.drones_page, Gtk.Box)
    assert isinstance(window.logs_page, Gtk.Box)
    assert isinstance(window.drone_view, Gtk.ColumnView)
    assert isinstance(window.log_view, Gtk.TextView)
    for name in ("start", "pause", "stop", "start_all", "pause_all", "stop_all"):
        assert isinstance(getattr(window, f"{name}_button"), Gtk.Button)


def test_stack_has_the_drones_and_logs_pages(make_window):
    _application, window = make_window()

    assert window.stack.get_child_by_name("drones") is window.drones_page
    assert window.stack.get_child_by_name("logs") is window.logs_page
    assert window.stack.get_pages().get_n_items() == 2


def test_the_view_switcher_is_in_the_header_bar(make_window):
    from gi.repository import Adw

    _application, window = make_window()

    switchers = []

    def walk(widget):
        if isinstance(widget, Adw.ViewSwitcher):
            switchers.append(widget)
        child = widget.get_first_child()
        while child is not None:
            walk(child)
            child = child.get_next_sibling()

    walk(window)

    assert len(switchers) == 1
    assert switchers[0].get_stack() is window.stack


def test_skeleton_window_has_no_rows_and_disabled_buttons(make_window):
    _application, window = make_window()

    assert window.drone_view.get_model().get_n_items() == 0
    for name in ("start", "pause", "stop", "start_all", "pause_all", "stop_all"):
        assert not getattr(window, f"{name}_button").get_sensitive()
