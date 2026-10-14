import logging
import threading
from typing import Iterator, List, Optional

import pytest

from ControlTower.CommunicationHandler import TelemetryPayload
from ControlTower.Scheduler import Scheduler
from ControlTower.common import Drone, DroneAnimationStatus, DroneStatus, Point
from tests.helpers.fakes import FakeClock, make_drone, telemetry

JOIN_TIMEOUT = 2.0


def no_telemetry() -> Iterator[Optional[TelemetryPayload]]:
    return iter(())


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def build(drones: List[Drone], operation, clock: FakeClock, telemetry_operation=no_telemetry) -> Scheduler:
    return Scheduler(drones, operation, telemetry_operation, sleep=clock.sleep, clock=clock)


def join(scheduler: Scheduler, drone: Drone) -> None:
    thread = scheduler.dispatcher_threads[drone.id]
    thread.join(JOIN_TIMEOUT)
    assert not thread.is_alive(), "dispatcher thread did not finish"


class TestFullRun:
    def test_every_frame_sent_once_in_order_with_step_updated_first(self, clock):
        drone = make_drone(0, timestamps=(0, 100, 300, 600))
        seen = []
        scheduler = build([drone], lambda d: seen.append(d.animation_step), clock)

        scheduler.start([drone])
        join(scheduler, drone)

        assert seen == [0, 1, 2, 3]

    def test_sleeps_are_timestamp_deltas_first_is_zero(self, clock):
        drone = make_drone(0, timestamps=(0, 100, 300, 600))
        scheduler = build([drone], lambda d: None, clock)

        scheduler.start([drone])
        join(scheduler, drone)

        assert clock.sleeps == pytest.approx([0.0, 0.1, 0.2, 0.3])

    def test_time_spent_in_operation_is_subtracted_from_next_delay(self, clock):
        drone = make_drone(0, timestamps=(0, 100, 300))
        scheduler = build([drone], lambda d: setattr(clock, "now", clock.now + 0.04), clock)

        scheduler.start([drone])
        join(scheduler, drone)

        assert clock.sleeps == pytest.approx([0.0, 0.06, 0.16])

    def test_operation_slower_than_delta_waits_zero(self, clock):
        drone = make_drone(0, timestamps=(0, 100))
        scheduler = build([drone], lambda d: setattr(clock, "now", clock.now + 5.0), clock)

        scheduler.start([drone])
        join(scheduler, drone)

        assert clock.sleeps == [0.0, 0.0]

    def test_single_frame_animation(self, clock):
        drone = make_drone(0, timestamps=(0,))
        seen = []
        scheduler = build([drone], lambda d: seen.append(d.animation_step), clock)

        scheduler.start([drone])
        join(scheduler, drone)

        assert seen == [0]
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_status_is_live_while_running_and_ended_after(self, clock):
        drone = make_drone(0)
        statuses = []
        scheduler = build([drone], lambda d: statuses.append(d.animation_status), clock)
        assert drone.animation_status is DroneAnimationStatus.READY

        scheduler.start([drone])
        join(scheduler, drone)

        assert set(statuses) == {DroneAnimationStatus.LIVE}
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_start_without_arguments_starts_all_drones(self, clock):
        drones = [make_drone(0), make_drone(1)]
        seen = set()
        scheduler = build(drones, lambda d: seen.add(d.id), clock)

        scheduler.start()
        for drone in drones:
            join(scheduler, drone)

        assert seen == {0, 1}

    def test_start_unknown_drone_is_logged_and_ignored(self, clock, caplog):
        scheduler = build([make_drone(0)], lambda d: None, clock)

        with caplog.at_level(logging.WARNING):
            scheduler.start([make_drone(99)])

        assert scheduler.dispatcher_threads == {}
        assert "99" in caplog.text


class TestDoubleStart:
    def test_second_start_does_not_raise_or_duplicate_frames(self, clock):
        drone = make_drone(0)
        hold = threading.Event()
        seen = []

        def operation(d: Drone) -> None:
            seen.append(d.animation_step)
            if d.animation_step == 0:
                assert hold.wait(JOIN_TIMEOUT)

        scheduler = build([drone], operation, clock)
        scheduler.start([drone])
        first_thread = scheduler.dispatcher_threads[0]

        scheduler.start([drone])
        assert scheduler.dispatcher_threads[0] is first_thread

        hold.set()
        join(scheduler, drone)
        assert seen == [0, 1, 2, 3]

    def test_listener_thread_started_once(self, clock):
        drones = [make_drone(0), make_drone(1)]
        calls = []
        release = threading.Event()

        def telemetry_operation():
            calls.append(1)
            release.wait(JOIN_TIMEOUT)
            yield None

        scheduler = build(drones, lambda d: None, clock, telemetry_operation)
        scheduler.start([drones[0]])
        listener = scheduler.listener_thread
        scheduler.start([drones[1]])
        scheduler.start()

        assert scheduler.listener_thread is listener
        release.set()
        listener.join(JOIN_TIMEOUT)
        assert calls == [1]


class TestPauseResume:
    def test_pause_holds_position_and_start_resumes_without_skipping(self, clock):
        drone = make_drone(0, timestamps=(0, 100, 200, 300, 400, 500))
        seen = []
        paused = threading.Event()

        def operation(d: Drone) -> None:
            seen.append(d.animation_step)
            if d.animation_step == 1:
                scheduler.pause([d])
                paused.set()

        scheduler = build([drone], operation, clock)
        scheduler.start([drone])
        assert paused.wait(JOIN_TIMEOUT)
        thread = scheduler.dispatcher_threads[0]

        thread.join(0.05)
        assert thread.is_alive()
        assert seen == [0, 1]
        assert drone.animation_step == 1
        assert drone.animation_status is DroneAnimationStatus.PAUSED

        scheduler.start([drone])
        join(scheduler, drone)

        assert scheduler.dispatcher_threads[0] is thread
        assert seen == [0, 1, 2, 3, 4, 5]
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_stop_while_paused_ends_thread(self, clock):
        drone = make_drone(0)
        seen = []
        paused = threading.Event()

        def operation(d: Drone) -> None:
            seen.append(d.animation_step)
            if d.animation_step == 1:
                scheduler.pause([d])
                paused.set()

        scheduler = build([drone], operation, clock)
        scheduler.start([drone])
        assert paused.wait(JOIN_TIMEOUT)

        scheduler.stop([drone])
        join(scheduler, drone)

        assert seen == [0, 1]
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_pausing_one_drone_leaves_others_running(self, clock):
        drones = [make_drone(0), make_drone(1)]
        seen = {0: [], 1: []}
        paused = threading.Event()

        def operation(d: Drone) -> None:
            seen[d.id].append(d.animation_step)
            if d.id == 0 and d.animation_step == 0:
                scheduler.pause([d])
                paused.set()

        scheduler = build(drones, operation, clock)
        scheduler.start()
        assert paused.wait(JOIN_TIMEOUT)
        join(scheduler, drones[1])

        assert seen[1] == [0, 1, 2, 3]
        assert seen[0] == [0]
        assert drones[0].animation_status is DroneAnimationStatus.PAUSED

        scheduler.stop([drones[0]])
        join(scheduler, drones[0])


class TestStop:
    def test_stop_mid_run_ends_loop_and_thread(self, clock):
        drone = make_drone(0, timestamps=(0, 100, 200, 300, 400, 500))
        seen = []

        def operation(d: Drone) -> None:
            seen.append(d.animation_step)
            if d.animation_step == 2:
                scheduler.stop([d])

        scheduler = build([drone], operation, clock)
        scheduler.start([drone])
        join(scheduler, drone)

        assert seen == [0, 1, 2]
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_stop_is_prompt_with_real_wait(self):
        drone = make_drone(0, timestamps=(0, 3_600_000))
        first_frame = threading.Event()
        scheduler = Scheduler([drone], lambda d: first_frame.set(), no_telemetry)

        scheduler.start([drone])
        assert first_frame.wait(JOIN_TIMEOUT)
        scheduler.stop([drone])

        scheduler.dispatcher_threads[0].join(JOIN_TIMEOUT)
        assert not scheduler.dispatcher_threads[0].is_alive()
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_pause_resume_stop_on_unstarted_drone_do_not_raise(self, clock):
        drone = make_drone(0)
        scheduler = build([drone], lambda d: None, clock)

        scheduler.pause([drone])
        scheduler.stop([drone])

        assert drone.animation_status is DroneAnimationStatus.READY
        assert scheduler.dispatcher_threads == {}

    def test_pause_and_stop_on_finished_drone_keep_ended(self, clock):
        drone = make_drone(0)
        scheduler = build([drone], lambda d: None, clock)
        scheduler.start([drone])
        join(scheduler, drone)

        scheduler.pause([drone])
        scheduler.stop([drone])

        assert drone.animation_status is DroneAnimationStatus.ENDED


class TestRestart:
    def test_start_after_stop_restarts_from_frame_zero_on_new_thread(self, clock):
        drone = make_drone(0)
        seen = []
        stop_once = [True]

        def operation(d: Drone) -> None:
            seen.append(d.animation_step)
            if d.animation_step == 1 and stop_once[0]:
                stop_once[0] = False
                scheduler.stop([d])

        scheduler = build([drone], operation, clock)
        scheduler.start([drone])
        join(scheduler, drone)
        first_thread = scheduler.dispatcher_threads[0]
        assert seen == [0, 1]

        scheduler.start([drone])
        join(scheduler, drone)

        assert scheduler.dispatcher_threads[0] is not first_thread
        assert seen == [0, 1, 0, 1, 2, 3]
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_start_after_natural_end_replays_animation(self, clock):
        drone = make_drone(0)
        seen = []
        scheduler = build([drone], lambda d: seen.append(d.animation_step), clock)

        scheduler.start([drone])
        join(scheduler, drone)
        scheduler.start([drone])
        join(scheduler, drone)

        assert seen == [0, 1, 2, 3, 0, 1, 2, 3]


class TestNonContiguousIds:
    def test_drones_with_gaps_in_ids_run(self, clock):
        drones = [make_drone(2), make_drone(5), make_drone(9)]
        seen = set()
        scheduler = build(drones, lambda d: seen.add(d.id), clock)

        scheduler.start()
        for drone in drones:
            join(scheduler, drone)

        assert seen == {2, 5, 9}
        assert set(scheduler.dispatcher_threads) == {2, 5, 9}


class TestTelemetry:
    def run_listener(self, scheduler: Scheduler, drone: Drone) -> None:
        scheduler.start([drone])
        scheduler.listener_thread.join(JOIN_TIMEOUT)
        assert not scheduler.listener_thread.is_alive()
        join(scheduler, drone)

    def test_telemetry_updates_drone_by_id(self, clock):
        drones = [make_drone(2), make_drone(5)]
        items = [telemetry(5, x=2.0, status=DroneStatus.LOST)]
        scheduler = build(drones, lambda d: None, clock, lambda: iter(items))

        self.run_listener(scheduler, drones[0])

        assert drones[1].status is DroneStatus.LOST
        assert drones[1].reported_position == Point(2.0, -1.5, 0.0)
        assert drones[0].status is DroneStatus.OK

    def test_unknown_drone_id_is_logged_and_listener_keeps_running(self, clock, caplog):
        drones = [make_drone(2), make_drone(5)]
        items = [telemetry(77), telemetry(5, status=DroneStatus.INACTIVE)]
        scheduler = build(drones, lambda d: None, clock, lambda: iter(items))

        with caplog.at_level(logging.WARNING):
            self.run_listener(scheduler, drones[0])

        assert "77" in caplog.text
        assert drones[1].status is DroneStatus.INACTIVE

    def test_none_payloads_are_ignored(self, clock):
        drones = [make_drone(2)]
        items = [None, telemetry(2, status=DroneStatus.INACTIVE), None]
        scheduler = build(drones, lambda d: None, clock, lambda: iter(items))

        self.run_listener(scheduler, drones[0])

        assert drones[0].status is DroneStatus.INACTIVE

    def test_non_telemetry_items_are_ignored(self, clock):
        drones = [make_drone(2)]
        items = ["junk", telemetry(2, status=DroneStatus.INACTIVE)]
        scheduler = build(drones, lambda d: None, clock, lambda: iter(items))

        self.run_listener(scheduler, drones[0])

        assert drones[0].status is DroneStatus.INACTIVE

    def test_exception_in_telemetry_operation_is_logged_not_raised(self, clock, caplog):
        drone = make_drone(0)

        def failing():
            raise RuntimeError("serial exploded")
            yield

        scheduler = build([drone], lambda d: None, clock, failing)

        with caplog.at_level(logging.ERROR):
            self.run_listener(scheduler, drone)

        assert "serial exploded" in caplog.text


class TestShutdown:
    def test_shutdown_stops_listener_and_dispatchers(self, clock):
        drone = make_drone(0)
        paused = threading.Event()
        idle = threading.Event()

        def operation(d: Drone) -> None:
            scheduler.pause([d])
            paused.set()

        def telemetry_operation():
            while True:
                idle.wait(0.001)
                yield None

        scheduler = build([drone], operation, clock, telemetry_operation)
        scheduler.start([drone])
        assert paused.wait(JOIN_TIMEOUT)

        scheduler.shutdown()

        scheduler.listener_thread.join(JOIN_TIMEOUT)
        assert not scheduler.listener_thread.is_alive()
        assert not scheduler.dispatcher_threads[0].is_alive()
        assert drone.animation_status is DroneAnimationStatus.ENDED

    def test_listener_can_start_again_after_shutdown(self, clock):
        drone = make_drone(0)
        calls = []

        def telemetry_operation():
            calls.append(1)
            while True:
                yield None

        scheduler = build([drone], lambda d: None, clock, telemetry_operation)
        scheduler.start([drone])
        scheduler.shutdown()
        scheduler.listener_thread.join(JOIN_TIMEOUT)

        scheduler.start([drone])
        scheduler.shutdown()
        scheduler.listener_thread.join(JOIN_TIMEOUT)

        assert calls == [1, 1]

    def test_shutdown_before_start_does_not_raise(self, clock):
        build([make_drone(0)], lambda d: None, clock).shutdown()
