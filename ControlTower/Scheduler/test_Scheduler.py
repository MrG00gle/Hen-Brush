import pytest
import logging
from .Scheduler import Scheduler
from ..common import *
from ..common.testing import generate_drones

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

class TestScheduler:

    def test_start(self):
        """
        Simple test to make sure that the scheduler is working.
        """
        drones = generate_drones(num_drones=3, anim_lenght=20)
        for drone in drones:
            logging.debug(f"Created Drone: {drone}")

        def operation(drone: Drone) -> None:
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

        scheduler = Scheduler(drones=drones, dispatcher_operation=operation, daemon=False)
        scheduler.start()
        for thread in scheduler.threads:
            thread.join()

        assert True
