from ControlTower.common import Command
from .utils import decode_command_payload
from ..payload import CommandPayload

class TestCommandPayload:

    def test_init(self):
        drone_id = 10
        command = Command.ARM
        com_payload = CommandPayload(drone_id, command)
        actual_drone_id, command_value = decode_command_payload(com_payload.payload)

        assert len(com_payload.payload) == 2
        assert actual_drone_id == drone_id
        assert command_value == command.value