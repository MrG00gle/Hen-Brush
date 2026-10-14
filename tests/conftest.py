"""Shared pytest configuration.
Fixtures live in ``tests/helpers`` and are registered here by explicit import
(not via ``pytest_plugins``, which recent pytest rejects in non-root conftest files).
"""
from tests.helpers.factories import (  # noqa: F401
    animation_dir,
    make_colors,
    make_drones,
    make_flight_paths,
    make_timestamps,
    rng,
)
from tests.helpers.fake_serial import (  # noqa: F401
    fake_handler,
    fake_serial,
    loop_handler,
    loop_serial_url,
)
