if __name__ == "__main__":
    from ControlTower.common.Animation import Animation
    from ControlTower.common.Color import Color
    from ControlTower.common.Command import Command
    from ControlTower.common.Drone import Drone
    from ControlTower.common.DroneAnimationSatus import DroneAnimationStatus
    from ControlTower.common.DroneStatus import DroneStatus
    from ControlTower.common.Point import Point
    from ControlTower.common.errors import ConfigFileKeyError, DroneFileNameReadError, SerialError
else:
    from .Animation import Animation
    from .Color import Color
    from .Command import Command
    from .Drone import Drone
    from .DroneAnimationSatus import DroneAnimationStatus
    from .DroneStatus import DroneStatus
    from .Point import Point
    from .errors import ConfigFileKeyError, DroneFileNameReadError, SerialError, SerialConfigLoadFailed
    import test

__all__ = [
    "Animation",
    "Color",
    "Command",
    "Drone",
    "DroneAnimationStatus",
    "DroneStatus",
    "Point",
    "ConfigFileKeyError",
    "DroneFileNameReadError",
    "SerialError",
    "SerialConfigLoadFailed"
]
