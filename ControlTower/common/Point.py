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

from dataclasses import dataclass

@dataclass
class Point:
    _X: float
    _Y: float
    _Z: float

    def __init__(self, x: float, y: float, z: float) -> None:
        self._X = x
        self._Y = y
        self._Z = z

    def __repr__(self) -> str:
        return f"{self.X} {self.Y} {self.Z}"

    @property
    def X(self):
        return self._X

    @property
    def Y(self):
        return self._Y

    @property
    def Z(self):
        return self._Z
