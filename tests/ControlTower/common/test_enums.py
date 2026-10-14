import pytest

import ControlTower.common as common
from ControlTower.common import Command, DroneAnimationStatus, DroneStatus

# Command and DroneStatus values are part of the wire protocol: changing them breaks the firmware.


class TestCommand:

    @pytest.mark.parametrize(
        "name, value",
        [("TELEMETRY_REQUEST", 1), ("ARM", 2), ("POSITION_COLOR", 3), ("POSITION", 4), ("RTH", 5), ("DISARM", 6)],
    )
    def test_values(self, name, value):
        assert Command[name].value == value
        assert Command(value) is Command[name]

    def test_has_exactly_the_known_members(self):
        assert [member.name for member in Command] == [
            "TELEMETRY_REQUEST", "ARM", "POSITION_COLOR", "POSITION", "RTH", "DISARM",
        ]

    @pytest.mark.parametrize("value", [0, 7, 255])
    def test_unknown_value_raises(self, value):
        with pytest.raises(ValueError):
            Command(value)


class TestDroneStatus:

    @pytest.mark.parametrize("name, value", [("LOST", 1), ("INACTIVE", 2), ("OK", 3)])
    def test_values(self, name, value):
        assert DroneStatus[name].value == value
        assert DroneStatus(value) is DroneStatus[name]

    def test_has_exactly_the_known_members(self):
        assert len(DroneStatus) == 3

    @pytest.mark.parametrize("value", [0, 4, 255])
    def test_unknown_value_raises(self, value):
        with pytest.raises(ValueError):
            DroneStatus(value)


class TestDroneAnimationStatus:

    @pytest.mark.parametrize("name, value", [("LIVE", 1), ("PAUSED", 2), ("ENDED", 3), ("READY", 4)])
    def test_values(self, name, value):
        assert DroneAnimationStatus[name].value == value
        assert DroneAnimationStatus(value) is DroneAnimationStatus[name]

    def test_has_exactly_the_known_members(self):
        assert len(DroneAnimationStatus) == 4

    @pytest.mark.parametrize("value", [0, 5])
    def test_unknown_value_raises(self, value):
        with pytest.raises(ValueError):
            DroneAnimationStatus(value)


def test_package_exports_every_name_in_all():
    for name in common.__all__:
        assert hasattr(common, name)
