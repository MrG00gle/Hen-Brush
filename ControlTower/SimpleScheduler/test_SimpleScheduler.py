import pytest
import logging
from .SimpleScheduler import SimpleScheduler
from ..common import *
from ..common.testing import generate_drones

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

class TestSimpleScheduler:

    def test_start(self):

        drones = generate_drones(num_drones=3, anim_lenght=20)

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
            logging.info(f"Drone: {drone.id}, Step: {drone.animation_step}, Status: {anim_status}")

        scheduler = SimpleScheduler(drones=drones, operation=operation, daemon=False)
        scheduler.start()
        for thread in scheduler.threads:
            thread.join()

        assert True
