import pytest
import logging
from ControlTower.common.Command import Command
from ControlTower.common.CommandPacket import CommandPacket

class TestCommandPacket:

    def test_init(self):
        com_packet = CommandPacket(drone_id=10, command=Command.ARM)
        assert com_packet is not None