"""Thread-safe, bounded log buffer fed by a ``logging`` handler and read by the UIs."""
import itertools
import logging
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Deque, Dict, List, Optional, Tuple

DEFAULT_CAPACITY = 1000


@dataclass(frozen=True)
class LogEntry:
    """One formatted log line.

    Attributes:
        seq: Sequence number, starting at 1 and growing by 1 for every entry ever emitted.
        level: Level name, e.g. ``"INFO"``.
        name: Name of the logger that emitted the record.
        message: The record formatted by the handler's formatter.
    """

    seq: int
    level: str
    name: str
    message: str


class LogBuffer(logging.Handler):
    """Logging handler that keeps the latest lines for a UI and notifies subscribers.

    Lines live in a bounded ring buffer. Every line gets a sequence number, so a UI can poll
    with ``read_since(cursor)`` and miss nothing that is still buffered, or ``subscribe`` and be
    called for each new line. Both are safe to use from any thread.

    Subscribers run on the thread that logged, outside the buffer's own lock. A UI toolkit
    that needs its main thread must hop over there itself (e.g. ``GLib.idle_add``).
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY, level: int = logging.NOTSET) -> None:
        """Create an empty buffer.

        Args:
            capacity: Maximum number of lines kept; older lines are dropped first.
            level: Minimum level this handler accepts.

        Raises:
            ValueError: If ``capacity`` is below 1.
        """
        if capacity < 1:
            raise ValueError(f"capacity must be at least 1, got {capacity}")
        super().__init__(level)
        self._entries: Deque[LogEntry] = deque(maxlen=capacity)
        self._subscribers: Dict[int, Callable[[LogEntry], None]] = {}
        self._tokens = itertools.count()
        self._next_seq = 1
        self._state_lock = Lock()
        self._installed_on: Optional[logging.Logger] = None
        self._previous_level: Optional[int] = None

    @property
    def capacity(self) -> int:
        """Maximum number of lines kept."""
        return self._entries.maxlen

    def emit(self, record: logging.LogRecord) -> None:
        """Store the record and notify the subscribers; failures go to ``handleError``."""
        try:
            message = self.format(record)
            with self._state_lock:
                entry = LogEntry(self._next_seq, record.levelname, record.name, message)
                self._next_seq += 1
                self._entries.append(entry)
                subscribers = list(self._subscribers.values())
        except Exception:
            self.handleError(record)
            return

        for callback in subscribers:
            try:
                callback(entry)
            except Exception:
                self.handleError(record)

    def entries(self) -> List[LogEntry]:
        """Snapshot of the buffered lines, oldest first."""
        with self._state_lock:
            return list(self._entries)

    def read_since(self, cursor: int = 0) -> Tuple[List[LogEntry], int]:
        """Lines newer than ``cursor``, for polling UIs.

        Args:
            cursor: Sequence number of the last line already seen; 0 reads everything buffered.

        Returns:
            ``(entries, new_cursor)``. Pass ``new_cursor`` to the next call. Lines that were
            dropped from the ring buffer in the meantime are skipped. Without new lines the
            cursor comes back unchanged.
        """
        with self._state_lock:
            if not self._entries:
                return [], cursor
            skip = max(0, cursor - self._entries[0].seq + 1)
            fresh = list(itertools.islice(self._entries, skip, None))
        if not fresh:
            return [], cursor
        return fresh, fresh[-1].seq

    def subscribe(self, callback: Callable[[LogEntry], None]) -> Callable[[], None]:
        """Call ``callback(entry)`` for every new line.

        Args:
            callback: Receives each new ``LogEntry``. An exception it raises is reported through
                ``handleError`` and affects neither the logging call nor other subscribers.

        Returns:
            A function that removes the subscription; calling it more than once is harmless.
        """
        with self._state_lock:
            token = next(self._tokens)
            self._subscribers[token] = callback

        def unsubscribe() -> None:
            with self._state_lock:
                self._subscribers.pop(token, None)

        return unsubscribe

    def install(self, logger: Optional[logging.Logger] = None, level: int = logging.INFO) -> None:
        """Attach this handler to a logger (the root logger by default).

        If the logger would drop records below ``level``, its level is lowered to ``level`` until
        ``uninstall()`` puts it back.

        Args:
            logger: Logger to attach to; None means the root logger.
            level: Minimum level this handler accepts.
        """
        self.uninstall()
        target = logger if logger is not None else logging.getLogger()
        self.setLevel(level)
        if target.getEffectiveLevel() > level:
            self._previous_level = target.level
            target.setLevel(level)
        target.addHandler(self)
        self._installed_on = target

    def uninstall(self) -> None:
        """Detach from the logger given to ``install()`` and restore its level. Does nothing if not installed."""
        target = self._installed_on
        if target is None:
            return
        target.removeHandler(self)
        if self._previous_level is not None:
            target.setLevel(self._previous_level)
        self._installed_on = None
        self._previous_level = None
