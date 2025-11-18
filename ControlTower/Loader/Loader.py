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

import csv
import json
import logging
import pathlib
import re
from typing import List, Tuple, Union

from ControlTower.common import Drone, Animation, Point, Color, ConfigFileKeyError, DroneFileNameReadError

class Loader:
    path: Union[pathlib.Path, pathlib.WindowsPath]

    def __init__(self, path :str):
        try:
            path = pathlib.Path(path)
            if path.exists() and path.is_dir():
                self.path = path
            else:
                raise FileNotFoundError
        except FileNotFoundError as e:
            logging.error("Provided path not found or is not a directory!")
        except Exception as e:
            logging.error(f"Encountered unexpected error({e}), while opening provided path: {path}")

    def load_config(self) -> Tuple[str, int, int] | None:
        """
        Method for loading json configuration, with defined structure:
            {
              "serial_port": "/dev/ttyUSB0",
              "serial_speed": 9600,
              "ping_timeout": 5
            }

        Returns:
             serial_port, serial_speed, ping_timeout or in case of error None
        """

        config_file = list(self.path.glob('*.json'))[0]
        if config_file:
            try:
                with config_file.open('r') as file:
                    config = json.load(file)
                    keys = ['serial_port', 'serial_speed', 'ping_timeout']
                    if  all(key in config for key in keys):
                        serial_port, serial_speed, ping_timeout = str(config['serial_port']), int(config['serial_speed']), int(config['ping_timeout'])
                        return serial_port, serial_speed, ping_timeout
                    else:
                        raise ConfigFileKeyError(f"Configuration file: {config_file}, misses or does not have conventionally named configuration entry's. Default configuration will be used!")
            except OSError:
                logging.error(f"Couldn't open/read config file: {config_file}, Default configuration will be used!")
            except ConfigFileKeyError as e:
                logging.error(str(e))
                return None
            except Exception as e:
                logging.error(f"Encountered unexpected error({e}), while working with: {config_file}")
                return None
        else:
            logging.warning(f"No config file with JSON format found in directory: {self.path} \n"
                            f"Default configuration will be used!")
            return None

    def load_drones(self) -> List[Drone]:
        pattern = "*.csv"
        regex = re.compile(r'^(drone_?|Drone_?)?[0-9]+\.csv$', re.IGNORECASE)
        drone_files = [f for f in self.path.glob(pattern) if regex.match(f.name)]
        drones = []

        for drone_file in drone_files:
            try:
                timestamps = []
                flight_path = []
                colors = []
                match = regex.match(drone_file.name)
                if match:
                    id = match.group(1)
                else:
                    raise DroneFileNameReadError(f"File: {drone_file}, does not match convention, and will be dropped!")

                with open(drone_file, 'r') as file:
                    csvreader = csv.reader(file)
                    for line in csvreader:
                        timestamps.append(int(line[0]))
                        flight_path.append(Point(x=float(line[1]), y=float(line[2]), z=float(line[3])))
                        colors.append(Color(r=int(line[4]), g=int(line[5]), b=int(line[6])))

                animation = Animation(timestamps=timestamps, flight_path=flight_path, colors=colors, path=drone_file)
                drones.append(Drone(id=id, animation=animation))
            except OSError:
                logging.error(f"Couldn't open/read file: {drone_file}, file will be dropped!")
                continue
            except DroneFileNameReadError as e:
                logging.error(str(e))
                continue
            except Exception as e:
                logging.error(f"Encountered unexpected error({e}), while working with: {drone_file}")
        return drones

    def load(self) -> Tuple[str, int, int, List[Drone]] | Tuple[None, None, None, List[Drone]]:
        """
        Methode for loading both config and drone list, or if in selected folder will not have configuration will return just drone list.

        Returns:
            serial_port, serial_speed, ping_timeout, drones or drones
        """
        serial_port, serial_speed, ping_timeout = self.load_config()
        drones = self.load_drones()
        if (serial_port, serial_speed, ping_timeout) is not None:
            return serial_port, serial_speed, ping_timeout, drones
        else:
            return None, None, None, drones
