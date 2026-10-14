import dataclasses
import logging
import threading

import pytest

from ControlTower.Presenter import LogBuffer, LogEntry


@pytest.fixture
def logger():
    """A private non-propagating logger, so tests never touch the root logger."""
    log = logging.getLogger("tests.presenter.logbuffer")
    log.setLevel(logging.DEBUG)
    log.propagate = False
    yield log
    log.handlers.clear()


@pytest.fixture
def buffer(logger):
    handler = LogBuffer(capacity=5)
    logger.addHandler(handler)
    return handler


def test_emit_stores_formatted_entries(buffer, logger):
    logger.info("hello %s", "world")
    logger.warning("careful")

    assert buffer.entries() == [
        LogEntry(1, "INFO", logger.name, "hello world"),
        LogEntry(2, "WARNING", logger.name, "careful"),
    ]


def test_uses_handler_formatter(buffer, logger):
    buffer.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.error("boom")
    assert buffer.entries()[0].message == "[ERROR] boom"


def test_entry_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        LogEntry(1, "INFO", "n", "m").message = "x"


def test_ring_buffer_drops_oldest(buffer, logger):
    for i in range(8):
        logger.info("line %d", i)

    entries = buffer.entries()
    assert [e.seq for e in entries] == [4, 5, 6, 7, 8]
    assert entries[0].message == "line 3"
    assert buffer.capacity == 5


def test_default_capacity():
    assert LogBuffer().capacity == 1000


def test_invalid_capacity():
    with pytest.raises(ValueError):
        LogBuffer(capacity=0)


def test_entries_is_a_snapshot(buffer, logger):
    logger.info("a")
    snapshot = buffer.entries()
    logger.info("b")
    assert len(snapshot) == 1


class TestReadSince:
    def test_reads_everything_from_cursor_zero(self, buffer, logger):
        logger.info("a")
        logger.info("b")
        entries, cursor = buffer.read_since(0)
        assert [e.message for e in entries] == ["a", "b"]
        assert cursor == 2

    def test_reads_only_new_entries(self, buffer, logger):
        logger.info("a")
        _, cursor = buffer.read_since(0)
        logger.info("b")
        entries, cursor = buffer.read_since(cursor)
        assert [e.message for e in entries] == ["b"]
        assert cursor == 2

    def test_nothing_new_keeps_cursor(self, buffer, logger):
        logger.info("a")
        _, cursor = buffer.read_since(0)
        assert buffer.read_since(cursor) == ([], cursor)

    def test_empty_buffer_keeps_cursor(self, buffer):
        assert buffer.read_since(0) == ([], 0)
        assert buffer.read_since(7) == ([], 7)

    def test_correct_after_old_lines_were_dropped(self, buffer, logger):
        logger.info("first")
        _, cursor = buffer.read_since(0)
        for i in range(10):
            logger.info("line %d", i)

        entries, cursor = buffer.read_since(cursor)

        assert [e.seq for e in entries] == [7, 8, 9, 10, 11]
        assert cursor == 11

    def test_cursor_at_the_oldest_kept_line(self, buffer, logger):
        for i in range(7):
            logger.info("line %d", i)
        entries, _ = buffer.read_since(3)
        assert [e.seq for e in entries] == [4, 5, 6, 7]


class TestSubscribe:
    def test_callback_receives_each_entry(self, buffer, logger):
        seen = []
        buffer.subscribe(seen.append)
        logger.info("a")
        logger.info("b")
        assert [e.message for e in seen] == ["a", "b"]

    def test_unsubscribe(self, buffer, logger):
        seen = []
        unsubscribe = buffer.subscribe(seen.append)
        logger.info("a")
        unsubscribe()
        unsubscribe()  # harmless twice
        logger.info("b")
        assert [e.message for e in seen] == ["a"]

    def test_same_callback_twice_is_independent(self, buffer, logger):
        seen = []
        first = buffer.subscribe(seen.append)
        buffer.subscribe(seen.append)
        first()
        logger.info("a")
        assert len(seen) == 1

    def test_failing_subscriber_is_isolated(self, buffer, logger, monkeypatch):
        reported = []
        monkeypatch.setattr(buffer, "handleError", reported.append)
        good = []

        def bad(entry):
            raise RuntimeError("subscriber bug")

        buffer.subscribe(bad)
        buffer.subscribe(good.append)

        logger.info("a")  # must not raise

        assert len(reported) == 1
        assert [e.message for e in good] == ["a"]
        assert [e.message for e in buffer.entries()] == ["a"]

    def test_subscriber_may_unsubscribe_itself(self, buffer, logger):
        seen = []
        holder = {}

        def once(entry):
            seen.append(entry)
            holder["unsubscribe"]()

        holder["unsubscribe"] = buffer.subscribe(once)
        logger.info("a")
        logger.info("b")
        assert len(seen) == 1

    def test_formatting_failure_goes_to_handle_error(self, buffer, monkeypatch):
        reported = []
        monkeypatch.setattr(buffer, "handleError", reported.append)
        record = logging.LogRecord("n", logging.INFO, __file__, 1, "%d", ("not a number",), None)

        buffer.emit(record)

        assert reported == [record]
        assert buffer.entries() == []


class TestInstall:
    @pytest.fixture
    def target(self):
        log = logging.getLogger("tests.presenter.install")
        log.propagate = False
        log.setLevel(logging.WARNING)
        yield log
        log.handlers.clear()
        log.setLevel(logging.NOTSET)

    def test_install_and_uninstall(self, target):
        handler = LogBuffer()
        handler.install(target, level=logging.INFO)
        assert handler in target.handlers

        target.info("visible")
        assert [e.message for e in handler.entries()] == ["visible"]

        handler.uninstall()
        assert handler not in target.handlers
        assert target.level == logging.WARNING

    def test_install_does_not_lower_a_more_verbose_logger(self, target):
        target.setLevel(logging.DEBUG)
        handler = LogBuffer()
        handler.install(target, level=logging.INFO)
        handler.uninstall()
        assert target.level == logging.DEBUG

    def test_handler_level_filters(self, target):
        handler = LogBuffer()
        handler.install(target, level=logging.ERROR)
        target.warning("hidden")
        target.error("shown")
        assert [e.message for e in handler.entries()] == ["shown"]
        handler.uninstall()

    def test_install_twice_attaches_once(self, target):
        handler = LogBuffer()
        handler.install(target)
        handler.install(target)
        assert target.handlers.count(handler) == 1
        handler.uninstall()

    def test_uninstall_without_install(self):
        LogBuffer().uninstall()

    def test_default_target_is_the_root_logger(self):
        root = logging.getLogger()
        before = root.level
        handler = LogBuffer()
        handler.install()
        try:
            assert handler in root.handlers
        finally:
            handler.uninstall()
        assert handler not in root.handlers
        assert root.level == before


def test_concurrent_emit_subscribe_unsubscribe(logger):
    buffer = LogBuffer(capacity=50)
    logger.addHandler(buffer)
    errors = []
    emitted_per_thread = 300
    threads_count = 4

    def emit():
        try:
            for i in range(emitted_per_thread):
                logger.info("line %d", i)
        except Exception as error:
            errors.append(error)

    def churn():
        try:
            for _ in range(300):
                buffer.subscribe(lambda entry: None)()
                buffer.entries()
                buffer.read_since(0)
        except Exception as error:
            errors.append(error)

    workers = [threading.Thread(target=emit) for _ in range(threads_count)] + [threading.Thread(target=churn)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)

    assert errors == []
    total = emitted_per_thread * threads_count
    entries = buffer.entries()
    assert len(entries) == 50
    assert [e.seq for e in entries] == list(range(total - 49, total + 1))
