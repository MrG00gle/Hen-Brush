"""Presenter turning drone state into display rows and button states, and user actions into controller calls."""
import logging
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Callable, List, Optional, Protocol

from ..common import Drone, DroneAnimationStatus
from .DroneRow import DroneRow

logger = logging.getLogger(__name__)

START_STATES = frozenset({DroneAnimationStatus.READY, DroneAnimationStatus.PAUSED, DroneAnimationStatus.ENDED})
PAUSE_STATES = frozenset({DroneAnimationStatus.LIVE})
STOP_STATES = frozenset({DroneAnimationStatus.LIVE, DroneAnimationStatus.PAUSED})


class Controller(Protocol):
    """What the presenter needs from the object that runs the drones (``ControlTower`` satisfies it)."""

    drones: List[Drone]

    def start(self, drones: Optional[List[Drone]] = None) -> None:
        """Start or resume the animation of ``drones`` (all drones when None)."""
        ...

    def pause(self, drones: Optional[List[Drone]] = None) -> None:
        """Pause the animation of ``drones`` (all drones when None)."""
        ...

    def stop(self, drones: Optional[List[Drone]] = None) -> None:
        """Stop the animation of ``drones`` (all drones when None)."""
        ...


@dataclass(frozen=True)
class ActionResult:
    """Outcome of a start/pause/stop request, with a message a UI can show or log.

    Attributes:
        ok: False if nothing was done or the controller raised.
        message: Human-readable description.
    """

    ok: bool
    message: str


@dataclass(frozen=True)
class ButtonStates:
    """Which buttons a UI should enable."""

    start: bool
    pause: bool
    stop: bool
    start_all: bool
    pause_all: bool
    stop_all: bool


def _title(value: Enum) -> str:
    """``DroneAnimationStatus.LIVE`` -> ``"Live"``."""
    return value.name.title()


class DronePresenter:
    """UI-agnostic view model over a controller: formatted rows, selection and actions.

    Both UIs render only what this class returns; no display formatting happens elsewhere.

    Thread safety: the scheduler threads mutate the drones while a UI reads. ``rows()`` and
    ``button_states()`` read each drone attribute exactly once into a local variable, so a
    single value is never torn. Different fields of one row may come from slightly different
    moments (e.g. the step from one frame and the position from the next); that is accepted.
    The selection is guarded by a lock.
    """

    def __init__(self, controller: Controller) -> None:
        """Create a presenter with nothing selected.

        Args:
            controller: Runs the drones; ``drones`` is read on every call.
        """
        self._controller = controller
        self._selection_lock = Lock()
        self._selected_id: Optional[int] = None

    # --- display ---------------------------------------------------------------------------

    def rows(self) -> List[DroneRow]:
        """Formatted rows of all drones, sorted by id."""
        rows = []
        for drone in sorted(self._controller.drones, key=lambda d: d.id):
            status = drone.status
            animation_status = drone.animation_status
            reported = drone.reported_position
            error = drone.position_error
            step = drone.animation_step
            length = drone.animation_len
            rows.append(DroneRow(
                drone_id=drone.id,
                status=_title(status),
                animation_status=_title(animation_status),
                position=f"{reported.X:.2f}, {reported.Y:.2f}, {reported.Z:.2f}",
                position_error=f"{error:.2f}",
                step_text=f"{step}/{length}",
                step=step,
                length=length,
            ))
        return rows

    # --- selection -------------------------------------------------------------------------

    @property
    def selected_id(self) -> Optional[int]:
        """Id of the selected drone, or None."""
        with self._selection_lock:
            return self._selected_id

    def select(self, drone_id: Optional[int]) -> bool:
        """Select a drone, or clear the selection with None.

        Args:
            drone_id: Id of a known drone, or None.

        Returns:
            False if the id is unknown; the previous selection is kept then.
        """
        if drone_id is not None and self._find(drone_id) is None:
            return False
        with self._selection_lock:
            self._selected_id = drone_id
        return True

    def _find(self, drone_id: int) -> Optional[Drone]:
        return next((drone for drone in self._controller.drones if drone.id == drone_id), None)

    def _selected(self) -> Optional[Drone]:
        selected_id = self.selected_id
        return None if selected_id is None else self._find(selected_id)

    # --- buttons ---------------------------------------------------------------------------

    def button_states(self) -> ButtonStates:
        """Which buttons to enable, from the current animation states.

        Start is enabled for READY/PAUSED/ENDED drones, Pause for LIVE, Stop for LIVE/PAUSED.
        The selected-drone buttons are off without a selection; the "all" buttons are on when
        any drone is in an applicable state.
        """
        states = [drone.animation_status for drone in self._controller.drones]
        selected = self._selected()
        selected_state = None if selected is None else selected.animation_status
        return ButtonStates(
            start=selected_state in START_STATES,
            pause=selected_state in PAUSE_STATES,
            stop=selected_state in STOP_STATES,
            start_all=any(state in START_STATES for state in states),
            pause_all=any(state in PAUSE_STATES for state in states),
            stop_all=any(state in STOP_STATES for state in states),
        )

    # --- actions ---------------------------------------------------------------------------

    def start_selected(self) -> ActionResult:
        """Start (or resume) the selected drone."""
        return self._act_selected("Start", self._controller.start)

    def pause_selected(self) -> ActionResult:
        """Pause the selected drone."""
        return self._act_selected("Pause", self._controller.pause)

    def stop_selected(self) -> ActionResult:
        """Stop the selected drone."""
        return self._act_selected("Stop", self._controller.stop)

    def start_all(self) -> ActionResult:
        """Start (or resume) all drones."""
        return self._act_all("Start", self._controller.start)

    def pause_all(self) -> ActionResult:
        """Pause all drones."""
        return self._act_all("Pause", self._controller.pause)

    def stop_all(self) -> ActionResult:
        """Stop all drones."""
        return self._act_all("Stop", self._controller.stop)

    def _act_selected(self, verb: str, action: Callable[[List[Drone]], None]) -> ActionResult:
        drone = self._selected()
        if drone is None:
            return ActionResult(False, "No drone selected")
        return self._act(verb, f"drone {drone.id}", action, [drone])

    def _act_all(self, verb: str, action: Callable[[List[Drone]], None]) -> ActionResult:
        drones = list(self._controller.drones)
        if not drones:
            return ActionResult(False, "No drones loaded")
        return self._act(verb, f"all drones ({len(drones)})", action, drones)

    @staticmethod
    def _act(verb: str, target: str, action: Callable[[List[Drone]], None], drones: List[Drone]) -> ActionResult:
        try:
            action(drones)
        except Exception as error:
            logger.exception("%s failed for %s", verb, target)
            return ActionResult(False, f"{verb} failed for {target}: {error}")
        return ActionResult(True, f"{verb} requested for {target}")
