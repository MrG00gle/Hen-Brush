import logging

from ControlTower.common import *
from ControlTower.CommunicationHandler.payload import *
from ControlTower.CommunicationHandler.PacketType import PacketType
from ControlTower.CommunicationHandler.CommunicationHandler import CommunicationHandler

# Important Note! : In order to run this test, you must setup a virtual serial port between "link=/dev/ttyV0" and /dev/ttyV1
# If you are using Linux system you can use "socat" tool to create a virtual serial port: socat PTY,link=/dev/ttyV0,raw,echo=0 PTY,link=/dev/ttyV1,raw,echo=0


class TestCommunicationHandler:

    def test_send_point_payload(self):
        send_payload = PointPayload(12, Point(10, 10, 10), Color(25, 25, 25))

        comm_send = CommunicationHandler(port="/dev/ttyV0")
        comm_listen = CommunicationHandler(port="/dev/ttyV1")



        while True:
            comm_send.send(send_payload)
            incomming_packet = comm_send.read_packet(timeout=1)
            if incomming_packet:
                packet_type = incomming_packet['type']
                incomming_payload = incomming_packet['payload']

                if packet_type == PacketType.POINT:
                    break

        assert incomming_payload == send_payload.payload
