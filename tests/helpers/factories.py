"""Test data factories, exposed as pytest fixtures (registered in tests/conftest.py).

Every fixture returns a callable, so a test can decide on the sizes it needs. All
randomness comes from the seeded ``rng`` fixture, so generated data is deterministic.
Sample animations live under pytest's ``tmp_path``; nothing is written to the repository.
"""

import csv
import json
import random
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pytest

from ControlTower.common import Animation, Color, Drone, Point

DEFAULT_SEED = 1234


@pytest.fixture
def rng() -> random.Random:
    """Seeded random generator shared by the factory fixtures."""
    return random.Random(DEFAULT_SEED)


@pytest.fixture
def make_timestamps(rng: random.Random) -> Callable[..., List[int]]:
    """Factory for lists of increasing timestamps in milliseconds."""

    def factory(
            count: int = 10,
            min_duration_ms: int = 100,
            max_duration_ms: int = 1000,
            start_timestamp_ms: int = 0,
    ) -> List[int]:
        """Generate timestamps with random durations between them.

        Args:
            count: Number of timestamps to generate.
            min_duration_ms: Minimum duration between timestamps in ms.
            max_duration_ms: Maximum duration between timestamps in ms.
            start_timestamp_ms: First timestamp in ms.

        Returns:
            List of timestamps in milliseconds.
        """
        timestamps = [start_timestamp_ms]
        for _ in range(count - 1):
            timestamps.append(timestamps[-1] + rng.randint(min_duration_ms, max_duration_ms))
        return timestamps

    return factory


@pytest.fixture
def make_flight_paths(rng: random.Random) -> Callable[..., List[List[Point]]]:
    """Factory for lists of random flight paths."""

    def factory(
            num_paths: int = 1,
            points_per_path: int = 10,
            start_point: Point = Point(0.0, 0.0, 0.0),
            min_z: Optional[float] = None,
            max_step_x: float = 10.0,
            max_step_y: float = 10.0,
            max_step_z: float = 5.0,
    ) -> List[List[Point]]:
        """Generate flight paths in 3D space. The z-coordinate never goes below the floor.

        Args:
            num_paths: Number of flight paths to generate.
            points_per_path: Number of points in each flight path.
            start_point: Starting point for all paths.
            min_z: Minimum z-value (floor). If None, uses start_point.Z.
            max_step_x: Maximum absolute step size in x-direction.
            max_step_y: Maximum absolute step size in y-direction.
            max_step_z: Maximum absolute step size in z-direction.

        Returns:
            A list of flight paths, where each path is a list of Point objects.
        """
        if min_z is None:
            min_z = start_point.Z

        paths = []
        for _ in range(num_paths):
            path = [start_point]
            for _ in range(points_per_path - 1):
                last_point = path[-1]
                new_x = last_point.X + rng.uniform(-max_step_x, max_step_x)
                new_y = last_point.Y + rng.uniform(-max_step_y, max_step_y)
                new_z = max(min_z, last_point.Z + rng.uniform(-max_step_z, max_step_z))
                path.append(Point(round(new_x, 2), round(new_y, 2), round(new_z, 2)))
            paths.append(path)
        return paths

    return factory


@pytest.fixture
def make_colors(rng: random.Random) -> Callable[..., List[List[Color]]]:
    """Factory for lists of lists of random colors."""

    def factory(num_lists: int = 1, colors_per_list: int = 5) -> List[List[Color]]:
        """Generate lists of Color objects with random RGB values.

        Args:
            num_lists: Number of lists to generate.
            colors_per_list: Number of Color objects per list.

        Returns:
            A list of lists, where each inner list contains Color objects.
        """
        return [
            [Color(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)) for _ in range(colors_per_list)]
            for _ in range(num_lists)
        ]

    return factory


@pytest.fixture
def make_drones(
        tmp_path: Path,
        make_timestamps: Callable[..., List[int]],
        make_flight_paths: Callable[..., List[List[Point]]],
        make_colors: Callable[..., List[List[Color]]],
) -> Callable[..., List[Drone]]:
    """Factory for drones with random animations. Animation paths point into ``tmp_path``."""

    def factory(num_drones: int, anim_length: int) -> List[Drone]:
        """Generate drones that share timestamps but have their own path and colors.

        Args:
            num_drones: Number of drones to generate (ids 0..num_drones-1).
            anim_length: Number of frames in every animation.

        Returns:
            List of drones.
        """
        timestamps = make_timestamps(
            count=anim_length,
            min_duration_ms=100,
            max_duration_ms=2000,
            start_timestamp_ms=0,
        )
        flight_paths = make_flight_paths(
            num_paths=num_drones,
            points_per_path=anim_length,
            start_point=Point(0.0, 0.0, 0.0),
            max_step_x=15.0,
            max_step_y=15.0,
            max_step_z=10.0,
        )
        color_lists = make_colors(num_lists=num_drones, colors_per_list=anim_length)

        drones = []
        for d in range(num_drones):
            animation = Animation(
                timestamps=timestamps,
                flight_path=flight_paths[d],
                colors=color_lists[d],
                path=tmp_path / f"drone_{d}.csv",
            )
            drones.append(Drone(id=d, animation=animation))
        return drones

    return factory


@pytest.fixture
def animation_dir(
        tmp_path: Path,
        make_timestamps: Callable[..., List[int]],
        make_flight_paths: Callable[..., List[List[Point]]],
        make_colors: Callable[..., List[List[Color]]],
) -> Callable[..., Path]:
    """Factory that writes a sample animation directory under ``tmp_path`` and returns it."""

    def factory(
            n_drones: int = 2,
            frames: int = 5,
            config: Optional[Dict[str, object]] = None,
            prefix: str = "drone_",
    ) -> Path:
        """Write ``<prefix><n>.csv`` files and an optional ``config.json``.

        CSV rows have no header and the columns ``ts,x,y,z,r,g,b``.

        Args:
            n_drones: Number of drone CSV files to write (numbered from 0).
            frames: Number of rows in each file.
            config: Content for ``config.json`` (e.g. ``serial_port``, ``serial_speed``,
                ``ping_timeout``). No config file is written when None.
            prefix: File name prefix, e.g. ``"drone_"``, ``"Drone"`` or ``""``.

        Returns:
            The directory containing the written files.
        """
        directory = tmp_path / "animation"
        directory.mkdir(parents=True, exist_ok=True)

        timestamps = make_timestamps(count=frames)
        paths = make_flight_paths(num_paths=n_drones, points_per_path=frames)
        colors = make_colors(num_lists=n_drones, colors_per_list=frames)

        for d in range(n_drones):
            with (directory / f"{prefix}{d}.csv").open("w", newline="") as file:
                writer = csv.writer(file)
                for ts, point, color in zip(timestamps, paths[d], colors[d]):
                    writer.writerow([ts, point.X, point.Y, point.Z, color.R, color.G, color.B])

        if config is not None:
            (directory / "config.json").write_text(json.dumps(config))
        return directory

    return factory
