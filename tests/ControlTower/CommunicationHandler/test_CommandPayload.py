from types import SimpleNamespace

import pytest

from ControlTower.common import Command
from ControlTower.CommunicationHandler.payload import CommandPayload
from tests.helpers.decoders import decode_command_payload


class TestCommandPayload:

    def test_init(self):
        drone_id = 10
        command = Command.ARM
        com_payload = CommandPayload(drone_id, command)
        actual_drone_id, command_value = decode_command_payload(com_payload.payload)

        assert len(com_payload.payload) == 2
        assert actual_drone_id == drone_id
        assert command_value == command.value

    def test_properties(self):
        com_payload = CommandPayload(3, Command.RTH)

        assert com_payload.drone_id == 3
        assert com_payload.command == Command.RTH
        assert com_payload.payload == bytes([3, 5])

    @pytest.mark.parametrize("command", list(Command))
    def test_every_command_is_used_verbatim(self, command):
        assert CommandPayload(1, command).payload == bytes([1, command.value])

    @pytest.mark.parametrize("drone_id", [0, 255])
    def test_valid_drone_ids(self, drone_id):
        assert CommandPayload(drone_id, Command.ARM).payload[0] == drone_id

    @pytest.mark.parametrize("drone_id", [-1, 256, "1", 1.5, None])
    def test_invalid_drone_ids_raise(self, drone_id):
        with pytest.raises(ValueError, match="Drone ID"):
            CommandPayload(drone_id, Command.ARM)

    @pytest.mark.parametrize("value", [-1, 256])
    def test_command_byte_out_of_range_raises(self, value):
        with pytest.raises(ValueError, match="command"):
            CommandPayload(1, SimpleNamespace(value=value))

    def test_repr(self):
        text = repr(CommandPayload(3, Command.RTH))

        assert text == "CommandPayload(ID: 3, COMMAND: 5, PACKET: 0305)"
