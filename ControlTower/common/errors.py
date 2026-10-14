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


class DroneFileNameReadError(Exception):
    """Raised by Loader when a drone file name has no recognizable id.

    The expected pattern is ``^(drone_?|Drone_?)?[0-9]+\\.csv$``. A .csv file with a flight path
    for some drone that does not follow this convention triggers the error.

    Attributes:
        message: The error text.
    """

    def __init__(self, message: str) -> None:
        """Create the error.

        Args:
            message: The error text.
        """
        self.message = message
        super().__init__(self.message)


class ConfigFileKeyError(Exception):
    """Raised by Loader when the .json config file misses a required entry or names one unconventionally.

    Attributes:
        message: The error text.
    """

    def __init__(self, message: str) -> None:
        """Create the error.

        Args:
            message: The error text.
        """
        self.message = message
        super().__init__(self.message)


class SerialConfigLoadFailed(Exception):
    """Raised by ControlTower when no direct serial configuration was given and loading it from file failed.

    Attributes:
        message: The error text.
    """

    def __init__(self, message: str) -> None:
        """Create the error.

        Args:
            message: The error text.
        """
        self.message = message
        super().__init__(self.message)


class SerialError(Exception):
    """Raised by CommunicationHandler when it can't open the serial port.

    Attributes:
        message: The error text.
    """

    def __init__(self, message: str) -> None:
        """Create the error.

        Args:
            message: The error text.
        """
        self.message = message
        super().__init__(self.message)
