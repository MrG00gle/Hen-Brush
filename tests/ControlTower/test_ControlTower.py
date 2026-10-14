import logging
import struct
import threading
from typing import Dict, List, Optional, Tuple

import numpy as np
import pytest
import serial

from ControlTower import ControlTower
from ControlTower.CommunicationHandler import CPointPayload, PacketType, PointPayload
from ControlTower.common import Color, Command, DroneAnimationStatus, DroneStatus, Point, SerialConfigLoadFailed
from tests.helpers.fakes import FakeClock, FakeComm, telemetry
from tests.helpers.frames import build_frame

FILE_CONFIG = {"serial_port": "COM9", "serial_speed": 9600, "ping_timeout": 5}
FILE_SERIAL = ("COM9", 9600, 5)
JOIN_TIMEOUT = 2.0


def expected_point_payload(drone_id: int, point: Point, command: Command = Command.POSITION) -> bytes:
    """Independently encoded POINT payload: id, command, x/y/z as little-endian float16."""
    return struct.pack("BB", drone_id, command.value) + np.array([point.X, point.Y, point.Z], dtype="<f2").tobytes()


def expected_cpoint_payload(drone_id: int, point: Point, color: Color) -> bytes:
    """Independently encoded CPOINT payload: POINT payload layout followed by r, g, b."""
    return (expected_point_payload(drone_id, point, Command.POSITION_COLOR)
            + bytes([color.R, color.G, color.B]))


@pytest.fixture
def serial_calls(monkeypatch, fake_serial) -> List[Tuple[tuple, dict]]:
    """Replace ``serial.serial_for_url`` with a recorder that returns the fake serial port."""
    calls = []

    def record(*args, **kwargs):
        calls.append((args, kwargs))
        return fake_serial

    monkeypatch.setattr(serial, "serial_for_url", record)
    return calls


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_tower(animation_dir, clock: FakeClock, comm: Optional[FakeComm] = None, n_drones: int = 2, frames: int = 4) -> ControlTower:
    directory = animation_dir(n_drones=n_drones, frames=frames)
    return ControlTower(str(directory), comm=comm or FakeComm(), sleep=clock.sleep, clock=clock)


def join_all(tower: ControlTower) -> None:
    for thread in tower.scheduler.dispatcher_threads.values():
        thread.join(JOIN_TIMEOUT)
        assert not thread.is_alive()


class TestSerialConfig:
    @pytest.mark.parametrize("direct, file_config, expected", [
        ({"serial_port": "COM1", "serial_speed": 115200, "serial_timeout": 2}, FILE_CONFIG, ("COM1", 115200, 2)),
        ({"serial_port": "COM1", "serial_speed": 0, "serial_timeout": 2}, FILE_CONFIG, ("COM1", 0, 2)),
        ({"serial_port": "COM1", "serial_speed": 115200, "serial_timeout": 0}, FILE_CONFIG, ("COM1", 115200, 0)),
        ({"serial_port": "COM1", "serial_speed": 115200, "serial_timeout": 2}, None, ("COM1", 115200, 2)),
        ({}, FILE_CONFIG, FILE_SERIAL),
        ({"serial_port": "COM1"}, FILE_CONFIG, FILE_SERIAL),
        ({"serial_port": "COM1", "serial_speed": 115200}, FILE_CONFIG, FILE_SERIAL),
        ({"serial_speed": 115200, "serial_timeout": 2}, FILE_CONFIG, FILE_SERIAL),
    ], ids=["direct-wins", "direct-speed-0", "direct-timeout-0", "direct-without-file",
            "file-only", "partial-port", "partial-no-timeout", "partial-no-port"])
    def test_precedence(self, animation_dir, serial_calls, direct, file_config, expected):
        directory = animation_dir(n_drones=1, config=file_config)

        tower = ControlTower(str(directory), **direct)

        assert len(serial_calls) == 1
        args, kwargs = serial_calls[0]
        assert (args[0], kwargs["baudrate"], kwargs["timeout"]) == expected
        assert tower.comm.port == expected[0]

    @pytest.mark.parametrize("direct", [{}, {"serial_port": "COM1"}, {"serial_port": "COM1", "serial_speed": 9600}],
                             ids=["nothing", "partial-port", "partial-no-timeout"])
    def test_no_usable_config_raises(self, animation_dir, serial_calls, caplog, direct):
        directory = animation_dir(n_drones=1)

        with caplog.at_level(logging.ERROR), pytest.raises(SerialConfigLoadFailed):
            ControlTower(str(directory), **direct)

        assert serial_calls == []
        assert "No serial config" in caplog.text

    def test_partial_direct_config_logs_warning(self, animation_dir, serial_calls, caplog):
        directory = animation_dir(n_drones=1, config=FILE_CONFIG)

        with caplog.at_level(logging.WARNING):
            ControlTower(str(directory), serial_port="COM1")

        assert "Incomplete direct serial config" in caplog.text

    def test_injected_comm_bypasses_serial_config(self, animation_dir, serial_calls):
        directory = animation_dir(n_drones=1)
        comm = FakeComm()

        tower = ControlTower(str(directory), comm=comm)

        assert tower.comm is comm
        assert serial_calls == []

    def test_missing_animation_directory_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ControlTower(str(tmp_path / "missing"), comm=FakeComm())


class TestSendToPoint:
    def test_pairs_drones_with_points(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm)
        points = [Point(1.0, 2.0, 3.0), Point(-4.0, 5.0, 6.5)]

        tower.send_to_point(tower.drones, points)

        assert len(comm.sent) == 2
        for payload, drone, point in zip(comm.sent, tower.drones, points):
            assert isinstance(payload, PointPayload)
            assert payload.drone_id == drone.id
            assert payload.point == point
            assert payload.payload == expected_point_payload(drone.id, point)

    def test_length_mismatch_raises_and_sends_nothing(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm)

        with pytest.raises(ValueError):
            tower.send_to_point(tower.drones, [Point(1.0, 2.0, 3.0)])

        assert comm.sent == []

    def test_empty_lists_send_nothing(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm)

        tower.send_to_point([], [])

        assert comm.sent == []

    def test_invalid_point_sends_nothing(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm)

        with pytest.raises(ValueError):
            tower.send_to_point(tower.drones, [Point(1.0, 2.0, 3.0), Point(1e9, 0.0, 0.0)])

        assert comm.sent == []


class TestDispatch:
    def test_run_sends_every_frame_as_cpoint_in_order(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm, n_drones=1, frames=5)
        drone = tower.drones[0]

        tower.start([drone])
        join_all(tower)

        expected = [expected_cpoint_payload(drone.id, point, color) for _, point, color in drone.animation]
        assert [type(p) for p in comm.sent] == [CPointPayload] * 5
        assert [p.payload for p in comm.sent] == expected
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_each_drone_sends_its_own_id(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm, n_drones=2, frames=3)

        tower.start()
        join_all(tower)

        by_id: Dict[int, int] = {}
        for payload in comm.sent:
            by_id[payload.drone_id] = by_id.get(payload.drone_id, 0) + 1
        assert by_id == {0: 3, 1: 3}

    def test_payload_bytes_over_loopback_serial(self, animation_dir):
        directory = animation_dir(n_drones=1, frames=4)
        tower = ControlTower(str(directory), serial_port="loop://", serial_speed=115200, serial_timeout=0.1)
        drone = tower.drones[0]
        drone.animation_step = 2
        _, point, color = drone.get_frame(2)

        try:
            tower._dispatch_operation(drone)
            packet = tower.comm.read_packet(timeout=0.5)
        finally:
            tower.comm.close()

        payload = expected_cpoint_payload(drone.id, point, color)
        assert packet["type"] is PacketType.CPOINT
        assert packet["payload"] == payload
        assert packet["raw"] == build_frame(PacketType.CPOINT.value, payload)


class TestControls:
    def test_start_pause_stop_forward_to_scheduler(self, animation_dir, clock):
        tower = make_tower(animation_dir, clock)
        calls = []

        class Spy:
            def start(self, drones=None): calls.append(("start", drones))
            def pause(self, drones=None): calls.append(("pause", drones))
            def stop(self, drones=None): calls.append(("stop", drones))

        tower.scheduler = Spy()
        drones = tower.drones[:1]

        tower.start(drones)
        tower.pause(drones)
        tower.stop(drones)

        assert calls == [("start", drones), ("pause", drones), ("stop", drones)]

    @pytest.mark.parametrize("action, text", [
        ("start", "Starting animation for Drones(0, 1)"),
        ("pause", "Pausing animation for Drones(0, 1)"),
        ("stop", "Stopping animation for Drones(0, 1)"),
    ])
    def test_actions_are_logged(self, animation_dir, clock, caplog, action, text):
        tower = make_tower(animation_dir, clock)

        with caplog.at_level(logging.INFO):
            getattr(tower, action)(tower.drones)
        tower.shutdown()

        assert text in caplog.text

    def test_pause_then_start_resumes(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm, n_drones=1, frames=4)
        drone = tower.drones[0]
        # Pause from inside the send of frame 1, so the interleaving is deterministic.
        original_send = comm.send
        paused = threading.Event()

        def send_and_pause(payload):
            original_send(payload)
            if len(comm.sent) == 2:
                tower.pause([drone])
                paused.set()

        comm.send = send_and_pause
        tower.start([drone])
        assert paused.wait(JOIN_TIMEOUT)
        assert drone.animation_status is DroneAnimationStatus.PAUSED
        assert len(comm.sent) == 2

        tower.start([drone])
        join_all(tower)

        assert len(comm.sent) == 4


class TestTelemetry:
    def test_telemetry_updates_drone_state(self, animation_dir, clock):
        comm = FakeComm([telemetry(1, x=2.0, status=DroneStatus.LOST), None])
        tower = make_tower(animation_dir, clock, comm)

        tower.start([tower.drones[0]])
        assert comm.drained.wait(JOIN_TIMEOUT)
        tower.shutdown()

        assert tower.drones[1].status is DroneStatus.LOST
        assert tower.drones[1].reported_position == Point(2.0, -1.5, 0.0)
        assert tower.drones[0].status is DroneStatus.OK


class TestShutdown:
    def test_shutdown_stops_scheduler_and_closes_comm(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm)
        tower.start()

        tower.shutdown()

        assert comm.closed
        tower.scheduler.listener_thread.join(JOIN_TIMEOUT)
        assert not tower.scheduler.listener_thread.is_alive()
        for thread in tower.scheduler.dispatcher_threads.values():
            assert not thread.is_alive()

    def test_shutdown_before_start(self, animation_dir, clock):
        comm = FakeComm()
        tower = make_tower(animation_dir, clock, comm)

        tower.shutdown()

        assert comm.closed
