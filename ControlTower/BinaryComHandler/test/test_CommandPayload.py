from ControlTower.common.Command import Command
from ControlTower.BinaryComHandler.payload.CommandPayload import CommandPayload

class TestCommandPayload:

    def test_init(self):
        com_packet = CommandPayload(drone_id=10, command=Command.ARM)
        assert com_packet is not None