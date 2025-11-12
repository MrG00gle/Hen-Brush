from time import sleep

import pytest
import logging
from typing import Generator

from ControlTower.Scheduler.Scheduler import Scheduler
from ControlTower.CommunicationHandler.CommunicationHandler import CommunicationHandler
from ControlTower.CommunicationHandler.payload.TelemetryPayload import TelemetryPayload
from ControlTower.CommunicationHandler.payload.PointPayload import PointPayload
from ControlTower.common import *
from ControlTower.common.testing import generate_drones

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

class TestScheduler:

    def test_start(self):
        """
        Simple test to make sure that the scheduler is working.
        """
        self.drones = generate_drones(num_drones=3, anim_lenght=10)
        for drone in self.drones:
            logging.debug(f"Created Drone: {drone}")

        self.telemetry_bytes_payload = bytes([
            0x0A,  # drone_id = 10
            0x40, 0x00,  # x = 2.0
            0xBE, 0x00,  # y = -1.5
            0x00, 0x00,  # z = 0.0
            0xFF, 0x00, 0x80,  # r=255, g=0, b=128
            0x03,  # drone_status = 3
            0x01  # drone_animation_status = 1
        ])

        def dispatcher_operation(drone: Drone) -> None:
            anim_status = ""
            match drone.animation_status:
                case DroneAnimationStatus.LIVE:
                    anim_status = "LIVE"
                case DroneAnimationStatus.PAUSED:
                    anim_status = "PAUSED"
                case DroneAnimationStatus.ENDED:
                    anim_status = "ENDED"
                case DroneAnimationStatus.READY:
                    anim_status = "READY"
            logging.debug(f"Drone: {drone.id}, Step: {drone.animation_step}, Status: {anim_status}")

        def telemetry_operation() -> Generator[TelemetryPayload, None, None]:
            for d in range(3):
                for a in range(20):
                    logging.debug(f"Got payload")
                    yield TelemetryPayload(payload=self.telemetry_bytes_payload)

        scheduler = Scheduler(drones=self.drones, dispatcher_operation=dispatcher_operation, telemetry_operation=telemetry_operation, daemon=False)
        scheduler.start()
        for thread in scheduler.dispatcher_threads:
            thread.join()
        sleep(15)
        assert True

    def test_start_integrated(self):
        """
        Test to make sure that the scheduler is working with CommunicationHandler.
        """
        self.drones = generate_drones(num_drones=3, anim_lenght=10)
        for drone in self.drones:
            logging.debug(f"Created Drone: {drone}")

        self.comm_send = CommunicationHandler(port="/dev/ttyV0")
        self.comm_listen = CommunicationHandler(port="/dev/ttyV1")

        def dispatcher_operation(drone: Drone) -> None:
            drone_id = drone.id
            _, point, color = drone.get_frame(drone.animation_step)
            command = Command.POSITION_COLOR
            payload = PointPayload(drone_id=drone_id, point=point, color=color, command=command)
            self.comm_send.send(payload=payload)

        scheduler = Scheduler(drones=self.drones, dispatcher_operation=dispatcher_operation, telemetry_operation=self.comm_listen.listen, daemon = False)
        scheduler.start()
        scheduler.listener_thread.join()
        for thread in scheduler.dispatcher_threads:
            thread.join()
        sleep(15)
        self.comm_send.close()
        self.comm_listen.close()
        assert True
