"""
// Copyright (C) 2025 Matsvei Kuzmiankou
//
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 3 of the License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with this program; if not, write to the Free Software Foundation,
// Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import logging
import serial

from ..common import *


class SerialHandler:
    ser: serial.Serial
    _port: str
    _baudrate: int

    def __init__(self, port: str, baudrate: int = 9600):
        self._port = port
        self._baudrate = baudrate
        message = ""
        try:
            self.ser = serial.Serial(port=self._port, baudrate=self._baudrate)
        except PermissionError as e:
            message = f"Cant proceed with opening serial port: {self._port}, Permission denied: {e}"
            logging.error(message)
        except FileNotFoundError:
            message = f"Port: {self._port}, not found."
            logging.error(message)
        except Exception as e:
            message = f"Unexpected error while opening serial connection: {e}"
            logging.error(message)
        finally:
            raise SerialError(message)

    def send_point(self, drone: Drone):
        if drone.get_frame(drone.animation_step) is None:
            return
        else:
            _, point, color = drone.get_frame(drone.animation_step)

        drone_id = drone.id
        packet = PointPacket(drone_id=drone_id, point=point, color=color).packet
        self.ser.write(packet)

    def send_telemetry(self, drone: Drone):
        """
        Sends telemetry request to drone.
        :arg drone Drone class
        """
        self.ser.write(CommandPacket(drone_id=drone.id, command=Command.TELEMETRY_REQUEST).packet)

    def listen_telemetry(self):     #TODO https://www.pyserial.com/docs/reading-data
        pass
