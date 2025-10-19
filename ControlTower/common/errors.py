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
    """
    Custom error for Loader class.
    Raised when regex(r'^(drone_?|Drone_?)?[0-9]+\.csv$') does not find an ID for drone.
    Basically that means that the .csv file with a flightpath for some drone does not math convention.
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class ConfigFileKeyError(Exception):
    """
    Custom error for Loader class.
    Raised when .json config file misses or does not have conventionally named configuration entry's.
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)