"""In-memory serial port for tests that need to control exactly what arrives and when.

pyserial's ``loop://`` URL is used for byte-exact round trips (what is written can be read
back from the same object, on Windows and Linux, no external setup). ``loop://`` cannot
simulate partial frames arriving over time, garbage, or silence, so ``FakeSerial`` covers those.
"""

from collections import deque
from typing import Deque, List

import pytest
import serial

from ControlTower.CommunicationHandler import CommunicationHandler


class FakeSerial:
    """Minimal stand-in for ``serial.Serial`` with scripted input.

    Attributes:
        written: Every ``bytes`` object passed to ``write``, in order.
    """

    def __init__(self) -> None:
        self._rx = bytearray()
        self._pending: Deque[bytes] = deque()
        self._open = True
        self.written: List[bytes] = []

    def feed(self, data: bytes) -> None:
        """Make ``data`` available to ``read`` immediately."""
        self._rx += data

    def feed_chunks(self, *chunks: bytes) -> None:
        """Queue chunks that become readable one at a time.

        A chunk is released only when ``in_waiting`` is polled while no data is waiting, so the
        reader sees each chunk on its own, like bytes trickling in over a slow link.
        """
        self._pending.extend(chunks)

    @property
    def in_waiting(self) -> int:
        """Number of bytes ready to be read."""
        if not self._rx and self._pending:
            self._rx += self._pending.popleft()
        return len(self._rx)

    @property
    def is_open(self) -> bool:
        """Whether ``close`` has not been called yet."""
        return self._open

    def write(self, data: bytes) -> int:
        """Record ``data`` and report it as fully written."""
        self.written.append(bytes(data))
        return len(data)

    def read(self, size: int = 1) -> bytes:
        """Return and consume up to ``size`` waiting bytes (never blocks)."""
        chunk = bytes(self._rx[:size])
        del self._rx[:size]
        return chunk

    def close(self) -> None:
        """Mark the port as closed."""
        self._open = False


@pytest.fixture
def loop_serial_url() -> str:
    """URL of pyserial's in-process loopback port."""
    return "loop://"


@pytest.fixture
def fake_serial() -> FakeSerial:
    """A fresh ``FakeSerial``."""
    return FakeSerial()


@pytest.fixture
def loop_handler(loop_serial_url: str):
    """A ``CommunicationHandler`` on ``loop://`` whose own writes can be read back."""
    handler = CommunicationHandler(port=loop_serial_url, timeout=0.05)
    yield handler
    handler.close()


@pytest.fixture
def fake_handler(monkeypatch: pytest.MonkeyPatch, fake_serial: FakeSerial) -> CommunicationHandler:
    """A ``CommunicationHandler`` wired to ``fake_serial`` through ``serial.serial_for_url``."""
    monkeypatch.setattr(serial, "serial_for_url", lambda *args, **kwargs: fake_serial)
    return CommunicationHandler(port="fake://", timeout=0.05)
