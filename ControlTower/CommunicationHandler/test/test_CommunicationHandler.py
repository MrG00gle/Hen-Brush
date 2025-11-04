import logging

from ControlTower.common import *
from ControlTower.CommunicationHandler.payload import *
from ControlTower.CommunicationHandler.PacketType import PacketType
from ControlTower.CommunicationHandler.CommunicationHandler import CommunicationHandler
from ControlTower.CommunicationHandler.test.test_utils import decode_point_payload

# Important Note! : In order to run this test, you must setup a virtual serial port between "link=/dev/ttyV0" and /dev/ttyV1
# If you are using Linux system you can use "socat" tool to create a virtual serial port: socat PTY,link=/dev/ttyV0,raw,echo=0 PTY,link=/dev/ttyV1,raw,echo=0


class TestCommunicationHandler:

    def test_send_point_payload(self):
        drone_id = 12
        point = Point(11, 12, 13)
        color = Color(25, 26, 27)
        send_payload = PointPayload(drone_id, point, color)

        comm_send = CommunicationHandler(port="/dev/ttyV0")
        comm_listen = CommunicationHandler(port="/dev/ttyV1")

        while True:
            comm_send.send(send_payload)
            incomming_packet = comm_send.read_packet(timeout=1)
            if incomming_packet:
                packet_type = incomming_packet['type']
                incomming_payload = incomming_packet['payload']
                decoded_payload = decode_point_payload(incomming_payload)

                if packet_type == PacketType.POINT:
                    break

        assert incomming_payload == send_payload.payload
        assert len(incomming_payload) == 11
        assert decoded_payload['drone_id'] == drone_id
        assert decoded_payload['command'] == Command.POSITION_COLOR.value
        assert decoded_payload['x'] == point.X
        assert decoded_payload['y'] == point.Y
        assert decoded_payload['z'] == point.Z
        assert decoded_payload['r'] == color.R
        assert decoded_payload['g'] == color.G
        assert decoded_payload['b'] == color.B
