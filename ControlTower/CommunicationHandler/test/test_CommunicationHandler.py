import logging
import threading
from ControlTower.common import *
from ControlTower.CommunicationHandler.payload import *
from ControlTower.CommunicationHandler.PacketType import PacketType
from ControlTower.CommunicationHandler.CommunicationHandler import CommunicationHandler

# Important Note! : In order to run this test, you must setup a virtual serial port between "link=/dev/ttyV0" and /dev/ttyV1
# If you are using Linux system you can use "socat" tool to create a virtual serial port: socat PTY,link=/dev/ttyV0,raw,echo=0 PTY,link=/dev/ttyV1,raw,echo=0


class TestCommunicationHandler:

    def test_send_point_payload(self):

        payload = PointPayload(12, Point(10, 10, 10), Color(25, 25, 25))

        comm_send = CommunicationHandler(port="/dev/ttyV0")
        comm_listen = CommunicationHandler(port="/dev/ttyV1")

        def send_thread():
            comm_send.send(payload)
            logging.debug(f"Sending packet: {payload}")

        threading.Thread(target=send_thread, args=()).start()
        incoming_packet = comm_listen.read_packet(timeout=1)

        if incoming_packet:
            packet_type = incoming_packet['type']
            incomming_payload = incoming_packet['payload']
            logging.debug(f"Got Packet with Type: {packet_type.name}, with Payload: {incomming_payload}")
            if packet_type == PacketType.POINT:
                assert incomming_payload == payload.payload


