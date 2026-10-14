"""Main window: a drone table and a log view over a ``DronePresenter`` and a ``LogBuffer``.

THREADING RULE
    Only the GTK main loop touches widgets. Scheduler, serial and logging threads only produce data:

    * the drone table is polled by ``GLib.timeout_add`` (``_on_tick`` runs on the main loop);
    * ``LogBuffer`` subscribers run on whatever thread logged, so ``_on_log_entry`` does nothing
      but ``GLib.idle_add``; the widget work happens in ``_drain_log`` on the main loop;
    * button handlers are GTK signal handlers, so they already run on the main loop.

    Never call a widget method from a subscriber, a scheduler operation or any thread of your own.
"""

import logging
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, GObject, Gtk  # noqa: E402

from ControlTower.Presenter import ActionResult, DronePresenter, DroneRow, LogBuffer  # noqa: E402

from .models import DroneItem  # noqa: E402
from .row_mapping import COLUMNS, diff_rows, excess_lines, row_values  # noqa: E402
from .ui_build import ensure_ui  # noqa: E402

logger = logging.getLogger(__name__)

UI_DIR = Path(__file__).resolve().parent / "ui"
BLP_FILE = UI_DIR / "window.blp"
# Compiled at import time, before the template decorator below needs the file.
UI_FILE = ensure_ui(BLP_FILE, UI_DIR / "window.ui")

REFRESH_INTERVAL_MS = 250
MAX_LOG_LINES = 2000


@Gtk.Template(filename=str(UI_FILE))
class HenBrushWindow(Adw.ApplicationWindow):
    """Drones page (column view plus start/pause/stop buttons) and logs page.

    Without a presenter the window is only the skeleton: empty pages, disabled buttons.
    """

    __gtype_name__ = "HenBrushWindow"

    toast_overlay = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    drones_page = Gtk.Template.Child()
    logs_page = Gtk.Template.Child()
    drone_view = Gtk.Template.Child()
    log_view = Gtk.Template.Child()
    start_button = Gtk.Template.Child()
    pause_button = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    start_all_button = Gtk.Template.Child()
    pause_all_button = Gtk.Template.Child()
    stop_all_button = Gtk.Template.Child()

    def __init__(self,
                 presenter: Optional[DronePresenter] = None,
                 log_buffer: Optional[LogBuffer] = None,
                 **kwargs) -> None:
        """Create the window and start feeding it.

        Args:
            presenter: Supplies rows and button states and runs the actions; None shows the skeleton only.
            log_buffer: Source of the log lines; None leaves the log view empty.
            **kwargs: Passed to ``Adw.ApplicationWindow`` (e.g. ``application=``).
        """
        super().__init__(**kwargs)
        self._presenter = presenter
        self._log_buffer = log_buffer
        self._closed = False
        self._tick_id: Optional[int] = None
        self._unsubscribe_log: Optional[Callable[[], None]] = None
        self._rows: Dict[int, DroneRow] = {}
        self._items: Dict[int, DroneItem] = {}
        self._log_cursor = 0
        self._log_drain_pending = False
        self._log_lock = threading.Lock()

        self._build_drone_view()
        self._build_log_view()
        self._connect_buttons()

        self.connect("close-request", self._on_close_request)
        self.connect("destroy", self._on_destroy)

        if presenter is not None:
            self._on_tick()
            self._tick_id = GLib.timeout_add(REFRESH_INTERVAL_MS, self._on_tick)
        if log_buffer is not None:
            self._unsubscribe_log = log_buffer.subscribe(self._on_log_entry)
            self._drain_log()

    # --- construction ------------------------------------------------------------------------

    def _build_drone_view(self) -> None:
        """Model, selection and one column per ``COLUMNS`` entry."""
        self._store = Gio.ListStore(item_type=DroneItem)
        self._selection = Gtk.SingleSelection(model=self._store, autoselect=False, can_unselect=True)
        self._selection.connect("notify::selected", self._on_selection_changed)
        self.drone_view.set_model(self._selection)

        for key, title in COLUMNS:
            column = Gtk.ColumnViewColumn(title=title, factory=self._make_factory(key))
            column.set_expand(True)
            self.drone_view.append_column(column)

    @staticmethod
    def _make_factory(key: str) -> Gtk.SignalListItemFactory:
        """Factory whose labels follow the ``key`` property of their row item."""
        factory = Gtk.SignalListItemFactory()

        def on_setup(_factory, list_item) -> None:
            list_item.set_child(Gtk.Label(xalign=0.0))

        def on_bind(_factory, list_item) -> None:
            label = list_item.get_child()
            item = list_item.get_item()
            # The binding lives on the label so on_unbind can find it again.
            label.henbrush_binding = item.bind_property(key, label, "label", GObject.BindingFlags.SYNC_CREATE)

        def on_unbind(_factory, list_item) -> None:
            label = list_item.get_child()
            binding = getattr(label, "henbrush_binding", None)
            if binding is not None:
                binding.unbind()
                label.henbrush_binding = None

        factory.connect("setup", on_setup)
        factory.connect("bind", on_bind)
        factory.connect("unbind", on_unbind)
        return factory

    def _build_log_view(self) -> None:
        """Wrap long lines and remember an end mark to scroll to."""
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_buffer = self.log_view.get_buffer()
        # Right gravity keeps the mark at the end while text is appended.
        self._end_mark = text_buffer.create_mark("end", text_buffer.get_end_iter(), False)

    def _connect_buttons(self) -> None:
        """Each button calls the presenter method of the same name."""
        actions = (
            (self.start_button, "start_selected"),
            (self.pause_button, "pause_selected"),
            (self.stop_button, "stop_selected"),
            (self.start_all_button, "start_all"),
            (self.pause_all_button, "pause_all"),
            (self.stop_all_button, "stop_all"),
        )
        for button, name in actions:
            button.connect("clicked", self._on_action_clicked, name)

    # --- drone table (main loop only) -------------------------------------------------------

    def _on_tick(self) -> bool:
        """Timer callback: update the table in place and refresh the buttons."""
        if self._closed or self._presenter is None:
            return GLib.SOURCE_REMOVE
        try:
            self._apply_rows(self._presenter.rows())
            self._refresh_buttons()
        except Exception:
            logger.exception("Refreshing the drone table failed")
        return GLib.SOURCE_CONTINUE

    def _apply_rows(self, rows) -> None:
        """Touch only the items that changed; selection and scroll position stay as they are."""
        diff = diff_rows(self._rows, rows)
        if diff.is_empty:
            return

        for drone_id in diff.removed:
            item = self._items.pop(drone_id)
            found, position = self._store.find(item)
            if found:
                self._store.remove(position)
            del self._rows[drone_id]

        for row in diff.changed:
            self._items[row.drone_id].update(row_values(row))
            self._rows[row.drone_id] = row

        for row in diff.added:
            item = DroneItem(row.drone_id, row_values(row))
            self._store.insert(self._insert_position(row.drone_id), item)
            self._items[row.drone_id] = item
            self._rows[row.drone_id] = row

    def _insert_position(self, drone_id: int) -> int:
        """Index that keeps the store sorted by drone id."""
        return sum(1 for known in self._items if known < drone_id)

    def _refresh_buttons(self) -> None:
        """Sensitivity comes from the presenter only."""
        states = self._presenter.button_states()
        self.start_button.set_sensitive(states.start)
        self.pause_button.set_sensitive(states.pause)
        self.stop_button.set_sensitive(states.stop)
        self.start_all_button.set_sensitive(states.start_all)
        self.pause_all_button.set_sensitive(states.pause_all)
        self.stop_all_button.set_sensitive(states.stop_all)

    def _on_selection_changed(self, selection, _pspec) -> None:
        if self._presenter is None:
            return
        item = selection.get_selected_item()
        self._presenter.select(None if item is None else item.drone_id)
        self._refresh_buttons()

    # --- buttons ----------------------------------------------------------------------------

    def _on_action_clicked(self, _button, name: str) -> None:
        """Run a presenter action and report its outcome in a toast."""
        if self._presenter is None:
            return
        result: ActionResult = getattr(self._presenter, name)()
        if not result.ok:
            logger.warning("%s", result.message)
        self.show_toast(result.message)
        self._refresh_buttons()

    def show_toast(self, message: str) -> None:
        """Queue a toast with ``message``."""
        self.toast_overlay.add_toast(Adw.Toast.new(message))

    # --- log view ---------------------------------------------------------------------------

    def _on_log_entry(self, _entry) -> None:
        """LogBuffer subscriber. Runs on the logging thread: it may only schedule work, never touch widgets."""
        with self._log_lock:
            if self._log_drain_pending or self._closed:
                return
            self._log_drain_pending = True
        GLib.idle_add(self._drain_log)

    def _drain_log(self) -> bool:
        """Append the lines that arrived since the last call. Runs on the main loop.

        Reading through ``LogBuffer.read_since`` keeps the lines in order and gap free even when
        several threads log at once, and it makes the first call the backfill.
        """
        with self._log_lock:
            self._log_drain_pending = False
        if self._closed or self._log_buffer is None:
            return GLib.SOURCE_REMOVE

        entries, self._log_cursor = self._log_buffer.read_since(self._log_cursor)
        if not entries:
            return GLib.SOURCE_REMOVE

        text_buffer = self.log_view.get_buffer()
        text = "".join(f"{entry.level:<8} {entry.message}\n" for entry in entries)
        text_buffer.insert(text_buffer.get_end_iter(), text)

        # The buffer ends with a newline, so it reports one line more than is shown.
        excess = excess_lines(text_buffer.get_line_count() - 1, MAX_LOG_LINES)
        if excess:
            start = text_buffer.get_start_iter()
            cut = text_buffer.get_start_iter()
            cut.forward_lines(excess)
            text_buffer.delete(start, cut)

        self.log_view.scroll_mark_onscreen(self._end_mark)
        return GLib.SOURCE_REMOVE

    # --- teardown ---------------------------------------------------------------------------

    def _stop_updates(self) -> None:
        """Stop the timer and the log subscription; safe to call more than once."""
        self._closed = True
        if self._tick_id is not None:
            GLib.source_remove(self._tick_id)
            self._tick_id = None
        if self._unsubscribe_log is not None:
            self._unsubscribe_log()
            self._unsubscribe_log = None

    def _on_close_request(self, _window) -> bool:
        self._stop_updates()
        return False

    def _on_destroy(self, _window) -> None:
        self._stop_updates()
