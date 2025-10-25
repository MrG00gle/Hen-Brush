import random
import time
from pathlib import Path
from typing import List
from .Point import Point
from .Color import Color
from .Drone import Drone
from .Animation import Animation

def generate_timestamps(
        count=10,
        min_duration_ms=100,
        max_duration_ms=1000,
        start_timestamp_ms=None
) -> List[int]:
    """
    Generate a list of timestamps in milliseconds with random durations between them.

    Parameters:
    - count (int): Number of timestamps to generate (default: 10)
    - min_duration_ms (int): Minimum duration between timestamps in ms (default: 100)
    - max_duration_ms (int): Maximum duration between timestamps in ms (default: 1000)
    - start_timestamp_ms (int): Starting timestamp in ms (default: current time)

    Returns:
    - list: List of timestamps in milliseconds
    """
    # Set start timestamp to current time if not provided
    if start_timestamp_ms is None:
        start_timestamp_ms = int(time.time() * 1000)

    # Initialize the list with the start timestamp
    timestamps = [start_timestamp_ms]

    # Generate subsequent timestamps
    for _ in range(count - 1):
        # Generate random duration between min and max
        duration = random.randint(min_duration_ms, max_duration_ms)
        # Add duration to the last timestamp
        next_timestamp = timestamps[-1] + duration
        timestamps.append(next_timestamp)

    return timestamps


def generate_flight_paths(
        num_paths: int = 1,
        points_per_path: int = 10,
        start_point: Point = Point(0.0, 0.0, 0.0),
        min_z: float = None,
        max_step_x: float = 10.0,
        max_step_y: float = 10.0,
        max_step_z: float = 5.0
) -> List[List[Point]]:
    """
    Generate multiple flight paths in 3D space, where each path is a list of Point objects.
    The z-coordinate never goes below the starting z (considered as the floor).

    Parameters:
    - num_paths (int): Number of flight paths to generate (default: 1)
    - points_per_path (int): Number of points in each flight path (default: 10)
    - start_point (Point): Starting point for all paths (default: Point(0.0, 0.0, 0.0))
    - min_z (float): Minimum z-value (floor). If None, uses start_point.Z (default: None)
    - max_step_x (float): Maximum absolute step size in x-direction (default: 10.0)
    - max_step_y (float): Maximum absolute step size in y-direction (default: 10.0)
    - max_step_z (float): Maximum absolute step size in z-direction (default: 5.0)

    Returns:
    - List[List[Point]]: A list of flight paths, where each path is a list of Point objects
    """
    if min_z is None:
        min_z = start_point.Z

    paths = []

    for _ in range(num_paths):
        path = [start_point]
        for _ in range(points_per_path - 1):
            last_point = path[-1]

            # Generate random steps
            dx = random.uniform(-max_step_x, max_step_x)
            dy = random.uniform(-max_step_y, max_step_y)
            dz = random.uniform(-max_step_z, max_step_z)

            # Calculate new position
            new_x = last_point.X + dx
            new_y = last_point.Y + dy
            new_z = last_point.Z + dz

            # Enforce floor constraint
            new_z = max(min_z, new_z)

            # Create new Point object
            new_point = Point(new_x, new_y, new_z)
            path.append(new_point)

        paths.append(path)

    return paths


def generate_color_lists(
        num_lists=1,
        colors_per_list=5
) -> List[List[Color]]:
    """
    Generate a list of lists of Color objects with random RGB values.

    Parameters:
    - num_lists (int): Number of lists to generate (default: 1)
    - colors_per_list (int): Number of Color objects per list (default: 5)

    Returns:
    - list: A list of lists, where each inner list contains Color objects
    """
    color_lists = []

    for _ in range(num_lists):
        color_list = []
        for _ in range(colors_per_list):
            # Generate random RGB values (0-255)
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            color_list.append(Color(r, g, b))
        color_lists.append(color_list)

    return color_lists


def generate_drones(num_drones: int, anim_lenght: int) -> List[Drone]:
    timestamps = generate_timestamps(
        count=anim_lenght,
        min_duration_ms=100,
        max_duration_ms=2000,
        start_timestamp_ms=0
    )

    flight_passes = generate_flight_paths(
        num_paths=anim_lenght,
        points_per_path=anim_lenght,
        start_point=Point(0.0, 0.0, 0.0),
        max_step_x=15.0,
        max_step_y=15.0,
        max_step_z=10.0
    )

    color_lists = generate_color_lists(
        num_lists=num_drones,
        colors_per_list=anim_lenght
    )

    drones = []

    for d in range(num_drones):
        animation = Animation(
            timestamps=timestamps,
            flight_path=flight_passes[d],
            colors=color_lists[d],
            path=Path(f"/test/drone{d}")
        )
        drone = Drone(id=d, animation=animation)
        drones.append(drone)

    return drones
