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
from typing import Dict, List, Optional, Tuple

from ControlTower.common import Animation, Color, ConfigFileKeyError, Drone, DroneFileNameReadError, Point

logger = logging.getLogger(__name__)

MAX_DRONE_ID = 255


class Loader:
    """Loads drone animations (``drone_<n>.csv``) and the optional serial config (``*.json``) from a directory.

    Parsing problems never raise: they are logged, and the affected config, file or row is skipped.

    Attributes:
        path: The animation directory.
    """

    path: pathlib.Path

    _CONFIG_KEYS = ('serial_port', 'serial_speed', 'ping_timeout')
    _DRONE_FILE = re.compile(r'^(?:drone_?)?(\d+)\.csv$', re.IGNORECASE)

    def __init__(self, path: str) -> None:
        """Check that the animation directory exists.

        Args:
            path: Directory with the drone CSV files and optional JSON config.

        Raises:
            FileNotFoundError: If the path does not exist.
            NotADirectoryError: If the path is not a directory.
        """
        directory = pathlib.Path(path)
        if not directory.exists():
            raise FileNotFoundError(f"Animation directory not found: {directory}")
        if not directory.is_dir():
            raise NotADirectoryError(f"Animation path is not a directory: {directory}")
        self.path = directory

    def load_config(self) -> Optional[Tuple[str, int, int]]:
        """Load the JSON configuration, with the structure::

            {
              "serial_port": "/dev/ttyUSB0",
              "serial_speed": 9600,
              "ping_timeout": 5
            }

        When the directory holds several JSON files, the first by sorted name is used.

        Returns:
            ``(serial_port, serial_speed, ping_timeout)``, or None if there is no usable config.
        """
        config_files = sorted(self.path.glob('*.json'))
        if not config_files:
            logger.warning("No config file with JSON format found in directory: %s. Default configuration will be used!", self.path)
            return None

        config_file = config_files[0]
        if len(config_files) > 1:
            logger.warning("Found %d JSON files in %s, using %s", len(config_files), self.path, config_file.name)

        try:
            with config_file.open('r') as file:
                config = json.load(file)
            if not isinstance(config, dict) or not all(key in config for key in self._CONFIG_KEYS):
                raise ConfigFileKeyError(f"Configuration file: {config_file}, misses or does not have conventionally named "
                                         f"configuration entries {self._CONFIG_KEYS}. Default configuration will be used!")
            return str(config['serial_port']), int(config['serial_speed']), int(config['ping_timeout'])
        except OSError:
            logger.error("Couldn't open/read config file: %s. Default configuration will be used!", config_file)
        except ConfigFileKeyError as error:
            logger.error("%s", error)
        except (ValueError, TypeError) as error:
            logger.error("Invalid config file %s (%s). Default configuration will be used!", config_file, error)
        return None

    def load_drones(self) -> List[Drone]:
        """Load every ``drone_<n>.csv`` (also ``Drone<n>.csv`` and ``<n>.csv``) in the directory.

        CSV rows have no header and the columns ``timestamp_ms,x,y,z,r,g,b``. The drone id is the
        number in the file name. Malformed rows are skipped, as are files without any valid row,
        duplicate ids and ids above 255 (they cannot be sent on the wire).

        Returns:
            The drones, sorted by id.
        """
        drones: Dict[int, Drone] = {}

        for drone_file in sorted(self.path.glob('*.csv')):
            try:
                match = self._DRONE_FILE.match(drone_file.name)
                if not match:
                    raise DroneFileNameReadError(f"File: {drone_file}, does not match convention, and will be dropped!")

                drone_id = int(match.group(1))
                if drone_id > MAX_DRONE_ID:
                    logger.error("File: %s has drone id %d, above the maximum of %d, and will be dropped!", drone_file, drone_id, MAX_DRONE_ID)
                    continue
                if drone_id in drones:
                    logger.error("File: %s repeats drone id %d, already loaded from %s, and will be dropped!",
                                 drone_file, drone_id, drones[drone_id].animation.path.name)
                    continue

                animation = self._load_animation(drone_file)
                if animation is None:
                    logger.error("File: %s has no valid rows and will be dropped!", drone_file)
                    continue
                drones[drone_id] = Drone(id=drone_id, animation=animation)
            except OSError:
                logger.error("Couldn't open/read file: %s, file will be dropped!", drone_file)
            except DroneFileNameReadError as error:
                logger.warning("%s", error)

        return [drones[drone_id] for drone_id in sorted(drones)]

    def _load_animation(self, drone_file: pathlib.Path) -> Optional[Animation]:
        """Parse one drone CSV file, skipping and logging malformed rows.

        Args:
            drone_file: CSV file to read.

        Returns:
            The animation, or None if the file has no valid row.

        Raises:
            OSError: If the file can't be read.
        """
        timestamps: List[int] = []
        flight_path: List[Point] = []
        colors: List[Color] = []

        with drone_file.open('r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                try:
                    timestamp = int(row[0])
                    point = Point(x=float(row[1]), y=float(row[2]), z=float(row[3]))
                    color = Color(r=int(row[4]), g=int(row[5]), b=int(row[6]))
                except (ValueError, IndexError) as error:
                    logger.warning("Skipping malformed row in %s, line %d: %r (%s)", drone_file, reader.line_num, row, error)
                    continue
                timestamps.append(timestamp)
                flight_path.append(point)
                colors.append(color)

        if not timestamps:
            return None
        return Animation(timestamps=timestamps, flight_path=flight_path, colors=colors, path=drone_file)

    def load(self) -> Tuple[Optional[str], Optional[int], Optional[int], List[Drone]]:
        """Load both the config and the drones.

        Returns:
            ``(serial_port, serial_speed, ping_timeout, drones)``; the first three are None when
            the directory has no usable config.
        """
        config = self.load_config()
        drones = self.load_drones()
        if config is None:
            return None, None, None, drones
        serial_port, serial_speed, ping_timeout = config
        return serial_port, serial_speed, ping_timeout, drones
