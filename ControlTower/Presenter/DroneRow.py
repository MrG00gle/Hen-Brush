"""Display-ready snapshot of one drone."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DroneRow:
    """Everything a UI shows about one drone, already formatted. UIs render these fields as they are.

    Attributes:
        drone_id: Id of the drone.
        status: Health status, e.g. ``"Ok"``.
        animation_status: Playback state, e.g. ``"Live"``.
        position: Reported position as ``"x.xx, y.yy, z.zz"``.
        position_error: Distance between expected and reported position, 2 decimals.
        step_text: Animation progress as ``"step/length"``, e.g. ``"3/10"``.
        step: Index of the current animation frame.
        length: Number of frames in the animation.
    """

    drone_id: int
    status: str
    animation_status: str
    position: str
    position_error: str
    step_text: str
    step: int
    length: int
