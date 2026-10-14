"""
// Copyright (C) 2025 Matsvei Kuzmiankou
//
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 3 of the License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with this program; if not, write to the Free Software Foundation,
// Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import logging
import time
from threading import Event, RLock, Thread, current_thread
from typing import Callable, Dict, Iterable, List, Optional

from ControlTower.CommunicationHandler import TelemetryPayload
from ControlTower.common import Drone, DroneAnimationStatus

logger = logging.getLogger(__name__)

SHUTDOWN_JOIN_TIMEOUT = 1.0


class _Run:
    """One playback of one drone's animation: its thread and the events that control it.

    Attributes:
        gate: Set while the drone may advance; cleared while it is paused.
        stop: Set to end the run.
        thread: The dispatcher thread of this run.
    """

    def __init__(self) -> None:
        self.gate = Event()
        self.gate.set()
        self.stop = Event()
        self.thread: Optional[Thread] = None


class Scheduler:
    """Plays the animation of each drone on its own thread and applies incoming telemetry.

    For frame ``k`` a dispatcher thread (1) waits while the drone is paused, (2) waits the
    timestamp delta to the previous frame, minus the time the previous operation took,
    (3) sets ``drone.animation_step = k`` and (4) calls ``operation(drone)``, so the operation
    always sees the step it has to send. After the last frame the drone is ``ENDED``.

    Lifecycle and restart policy:

    * ``start()`` on a drone that is not running (``READY`` or ``ENDED``, including after
      ``stop()``) creates a fresh thread. The animation restarts from frame 0.
    * ``start()`` on a ``PAUSED`` drone resumes it from the frame it holds. ``start()`` on a
      ``LIVE`` drone does nothing.
    * ``pause()`` holds a running drone at its current frame; no frame is skipped.
    * ``stop()`` ends a running or paused drone promptly. ``pause()`` and ``stop()`` on a
      drone that is not running do nothing.
    * The telemetry listener thread is started by the first ``start()`` and only once.
      ``shutdown()`` stops it together with all dispatchers; a later ``start()`` starts a new one.

    Drones are looked up by id, so ids need not be contiguous or start at 0.

    Attributes:
        drones: The drones this scheduler manages.
        dispatcher_threads: Latest dispatcher thread per drone id.
        listener_thread: The telemetry listener thread, or None before the first ``start()``.
    """

    drones: List[Drone]
    dispatcher_threads: Dict[int, Thread]
    listener_thread: Optional[Thread]

    def __init__(
            self,
            drones: List[Drone],
            dispatcher_operation: Callable[[Drone], None],
            telemetry_operation: Callable[[], Iterable[Optional[TelemetryPayload]]],
            *,
            daemon: bool = True,
            sleep: Optional[Callable[[float], None]] = None,
            clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create the scheduler; no thread runs until ``start()``.

        Args:
            drones: Drones to manage.
            dispatcher_operation: Called on a dispatcher thread for every frame, with
                ``drone.animation_step`` set to that frame.
            telemetry_operation: Called once on the listener thread; returns the iterable of
                telemetry payloads (``None`` items are ignored).
            daemon: Whether threads are daemon threads, so they never block interpreter exit.
            sleep: Replacement for the wait between frames, for tests. When None the wait is
                interruptible, so ``stop()`` takes effect immediately.
            clock: Monotonic clock in seconds, used to measure how long an operation took.
        """
        self.drones = drones
        self.dispatcher_threads = {}
        self.listener_thread = None
        self._drones_by_id: Dict[int, Drone] = {drone.id: drone for drone in drones}
        self._operation = dispatcher_operation
        self._telemetry_operation = telemetry_operation
        self._daemon = daemon
        self._sleep = sleep
        self._clock = clock
        self._lock = RLock()
        self._runs: Dict[int, _Run] = {}
        self._listener_active = False
        self._listener_stop = Event()

    def _resolve(self, drones: Optional[List[Drone]]) -> List[Drone]:
        """Map the given drones to the managed ones by id; None means all drones. Unknown ids are logged and skipped."""
        if drones is None:
            return list(self.drones)
        resolved = []
        for drone in drones:
            managed = self._drones_by_id.get(drone.id)
            if managed is None:
                logger.warning("Drone(%s) is not managed by this scheduler, ignoring", drone.id)
            else:
                resolved.append(managed)
        return resolved

    def _dispatch(self, drone: Drone, run: _Run) -> None:
        """Dispatcher thread body: play the animation of ``drone`` once."""
        try:
            previous_timestamp = 0
            spent = 0.0
            for step in range(drone.animation_len):
                timestamp = drone.get_frame(step)[0]
                delay = 0.0 if step == 0 else max(0.0, (timestamp - previous_timestamp) / 1000 - spent)

                if not self._pass_gate(run):
                    break
                self._wait(run, delay)
                if not self._pass_gate(run):
                    break

                drone.animation_step = step
                started = self._clock()
                self._operation(drone)
                spent = self._clock() - started
                previous_timestamp = timestamp
        finally:
            with self._lock:
                if self._runs.get(drone.id) is run:
                    drone.animation_status = DroneAnimationStatus.ENDED

    @staticmethod
    def _pass_gate(run: _Run) -> bool:
        """Block while the run is paused. Returns False if the run was stopped."""
        run.gate.wait()
        return not run.stop.is_set()

    def _wait(self, run: _Run, seconds: float) -> None:
        """Wait between frames: through the injected ``sleep``, or until ``stop`` is set."""
        if self._sleep is not None:
            self._sleep(seconds)
        else:
            run.stop.wait(seconds)

    def _listen(self, stop: Event) -> None:
        """Listener thread body: apply telemetry until the iterable ends or the listener is stopped."""
        try:
            for payload in self._telemetry_operation():
                if stop.is_set():
                    break
                self._apply_telemetry(payload)
        except Exception:
            logger.exception("Telemetry listener stopped because of an error")

    def _apply_telemetry(self, payload: object) -> None:
        """Copy the status and position of a telemetry payload to its drone."""
        if payload is None:
            return
        if not isinstance(payload, TelemetryPayload):
            logger.debug("Ignoring non-telemetry item: %r", payload)
            return
        drone = self._drones_by_id.get(payload.drone_id)
        if drone is None:
            logger.warning("Telemetry for unknown Drone(%s) ignored", payload.drone_id)
            return
        drone.status = payload.drone_status
        drone.reported_position = payload.point

    def _ensure_listener(self) -> None:
        """Start the listener thread unless it is already active."""
        if self._listener_active:
            return
        self._listener_active = True
        self._listener_stop = Event()
        self.listener_thread = Thread(name="Listener", target=self._listen, args=(self._listener_stop,), daemon=self._daemon)
        self.listener_thread.start()

    def start(self, drones: Optional[List[Drone]] = None) -> None:
        """Start, or resume, the animation of drones. See the class docstring for the restart policy.

        Args:
            drones: Drones to start; None starts all of them.
        """
        with self._lock:
            self._ensure_listener()
            for drone in self._resolve(drones):
                run = self._runs.get(drone.id)
                running = (
                    run is not None
                    and run.thread.is_alive()
                    and not run.stop.is_set()
                    and drone.animation_status in (DroneAnimationStatus.LIVE, DroneAnimationStatus.PAUSED)
                )
                if running:
                    if drone.animation_status is DroneAnimationStatus.PAUSED:
                        logger.info("Resuming Drone(%s)", drone.id)
                        drone.animation_status = DroneAnimationStatus.LIVE
                        run.gate.set()
                    else:
                        logger.debug("Drone(%s) is already running", drone.id)
                    continue

                logger.info("Starting: %s", drone.id)
                run = _Run()
                run.thread = Thread(name=f"Dispatcher_Thread({drone.id})", target=self._dispatch, args=(drone, run), daemon=self._daemon)
                drone.animation_step = 0
                drone.animation_status = DroneAnimationStatus.LIVE
                self._runs[drone.id] = run
                self.dispatcher_threads[drone.id] = run.thread
                run.thread.start()

    def pause(self, drones: Optional[List[Drone]] = None) -> None:
        """Hold running drones at their current frame. Drones that are not running are left alone.

        Args:
            drones: Drones to pause; None pauses all of them.
        """
        with self._lock:
            for drone in self._resolve(drones):
                run = self._runs.get(drone.id)
                if run is not None and run.thread.is_alive() and not run.stop.is_set() \
                        and drone.animation_status is DroneAnimationStatus.LIVE:
                    run.gate.clear()
                    drone.animation_status = DroneAnimationStatus.PAUSED
                    logger.info("Pausing Drone(%s)", drone.id)
                else:
                    logger.debug("Drone(%s) is not running, nothing to pause", drone.id)

    def stop(self, drones: Optional[List[Drone]] = None) -> None:
        """End the animation of running or paused drones. Drones that are not running are left alone.

        Args:
            drones: Drones to stop; None stops all of them.
        """
        with self._lock:
            for drone in self._resolve(drones):
                run = self._runs.get(drone.id)
                if run is not None and run.thread.is_alive() and not run.stop.is_set():
                    run.stop.set()
                    run.gate.set()
                    drone.animation_status = DroneAnimationStatus.ENDED
                    logger.info("Stopping Drone(%s)", drone.id)
                else:
                    logger.debug("Drone(%s) is not running, nothing to stop", drone.id)

    def shutdown(self) -> None:
        """Stop every dispatcher and the listener. A later ``start()`` starts a new listener.

        The listener exits the next time its telemetry source yields; closing the source
        (the serial port) makes that happen at once.
        """
        with self._lock:
            self._listener_stop.set()
            self._listener_active = False
            runs = list(self._runs.values())
            self.stop()
        for run in runs:
            if run.thread is not current_thread():
                run.thread.join(timeout=SHUTDOWN_JOIN_TIMEOUT)
