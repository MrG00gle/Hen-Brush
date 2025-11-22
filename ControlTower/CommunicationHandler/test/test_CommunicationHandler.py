import logging
import threading

from ControlTower.common import Point, Color, Command
from ..payload import PointPayload, CPointPayload
from ..PacketType import PacketType
from ..CommunicationHandler import CommunicationHandler
from .utils import decode_point_payload, decode_cpoint_payload

# Important Note! : In order to run this test, you must setup a virtual serial port between "link=/dev/ttyV0" and /dev/ttyV1
# If you are using Linux system you can use "socat" tool to create a virtual serial port: socat PTY,link=/dev/ttyV0,raw,echo=0 PTY,link=/dev/ttyV1,raw,echo=0


class TestCommunicationHandler:

    def test_send_point_payload(self):
        drone_id = 12
        point = Point(11, 12, 13)
        payload = PointPayload(drone_id, point)

        comm_send = CommunicationHandler(port="/dev/ttyV0")
        comm_listen = CommunicationHandler(port="/dev/ttyV1")

        def send_thread():
            comm_send.send(payload)
            logging.debug(f"Sending packet: {payload}")

        threading.Thread(target=send_thread, args=()).start()
        incoming_packet = comm_listen.read_packet(timeout=1)

        if incoming_packet:
            packet_type = incoming_packet['type']
            incoming_payload = incoming_packet['payload']
            decoded_payload = decode_point_payload(incoming_payload)
            logging.debug(f"Got Packet with Type: {packet_type.name}, with Payload: {incoming_payload}")
            if packet_type == PacketType.POINT:
                assert incoming_payload == payload.payload
                assert len(incoming_payload) == 8
                assert decoded_payload['drone_id'] == drone_id
                assert decoded_payload['command'] == Command.POSITION_COLOR.value
                assert decoded_payload['x'] == point.X
                assert decoded_payload['y'] == point.Y
                assert decoded_payload['z'] == point.Z

    def test_send_cpoint_payload(self):
        drone_id = 12
        point = Point(11, 12, 13)
        color = Color(25, 26, 27)
        payload = CPointPayload(drone_id, point, color)

        comm_send = CommunicationHandler(port="/dev/ttyV0")
        comm_listen = CommunicationHandler(port="/dev/ttyV1")

        def send_thread():
            comm_send.send(payload)
            logging.debug(f"Sending packet: {payload}")

        threading.Thread(target=send_thread, args=()).start()
        incoming_packet = comm_listen.read_packet(timeout=1)

        if incoming_packet:
            packet_type = incoming_packet['type']
            incoming_payload = incoming_packet['payload']
            decoded_payload = decode_cpoint_payload(incoming_payload)
            logging.debug(f"Got Packet with Type: {packet_type.name}, with Payload: {incoming_payload}")
            if packet_type == PacketType.POINT:
                assert incoming_payload == payload.payload
                assert len(incoming_payload) == 11
                assert decoded_payload['drone_id'] == drone_id
                assert decoded_payload['command'] == Command.POSITION_COLOR.value
                assert decoded_payload['x'] == point.X
                assert decoded_payload['y'] == point.Y
                assert decoded_payload['z'] == point.Z
                assert decoded_payload['r'] == color.R
                assert decoded_payload['g'] == color.G
                assert decoded_payload['b'] == color.B
