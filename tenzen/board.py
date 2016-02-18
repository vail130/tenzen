from __future__ import absolute_import, unicode_literals, print_function

import hashlib

from tenzen.colors import Color
from tenzen.group import Group
from tenzen.point import Point


class Board(object):
    def __init__(self, dimension):
        self.dimension = dimension
        self._points = tuple(tuple(Point(x, y, self) for y in range(dimension)) for x in range(dimension))

    def clone(self):
        clone = self.__class__(self.dimension)
        clone._points = tuple(tuple(p.clone(board=clone) for p in row) for row in self._points)
        return clone

    def get_state(self):
        return hashlib.md5(str(self)).digest()

    def is_complete(self):
        return all(p.is_occupied for row in self._points for p in row)

    def get_point(self, coordinates):
        x, y = coordinates
        try:
            return self._points[x][y]
        except IndexError:
            return None

    def add_piece(self, coordinates, color):
        x, y = coordinates
        try:
            self._points[x][y].fill(color)
        except IndexError:
            raise ValueError('[%s,%s] are invalid coordinates' % (x, y))

    def remove_captured_stones(self, color):
        self._remove_captured_groups(color)
        self._remove_captured_individuals(color)

    def _remove_captured_groups(self, color):
        covered_coordinates = set()
        for row in self._points:
            for point in row:
                if point.is_occupied and point.color == color and (point.x, point.y) not in covered_coordinates:
                    group = Group(point)
                    if group.is_captured:
                        group.clear()
                    covered_coordinates |= group.coordinates

    def _remove_captured_individuals(self, color):
        for row in self._points:
            for point in row:
                if point.is_occupied and point.color == color and point.is_captured:
                    point.clear()

    def calculate_territories(self):
        territory_counts = {
            Color.black: 0,
            Color.white: 0,
        }

        for row in self._points:
            for point in row:
                point.calculate_territory_color()
                if point.territory_color:
                    territory_counts[point.territory_color] += 1

        return territory_counts

    def __str__(self):
        transposed_points = zip(*self._points)
        a_z = ' '.join([str('  ')] + [str(unichr(ord('A') + i)) for i in range(self.dimension)])

        def format_number(n):
            return str(n) if n > 9 else str(' %s' % n)

        return '\n'.join(
            [a_z] +
            [' '.join(
                [format_number(j + 1)] + [str(p) for p in row]
            ) for j, row in enumerate(transposed_points)]
        )
