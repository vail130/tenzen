from __future__ import absolute_import, unicode_literals, print_function

import hashlib
from operator import itemgetter


class Group(object):
    def __init__(self, points, auto_find=True):
        self._original_points = points[:]
        self.points = points
        self.color = points[0].color
        self.coordinates = {(p.x, p.y) for p in points}
        self._state = None

        self.top = None
        self.bottom = None
        self.left = None
        self.right = None

        for p in self._original_points:
            if self.top is None or self.top.y > p.y:
                self.top = p
            if self.bottom is None or self.bottom.y < p.y:
                self.bottom = p
            if self.left is None or self.left.x > p.x:
                self.left = p
            if self.right is None or self.right.x < p.x:
                self.right = p

        if auto_find:
            for p in self._original_points:
                self._find_connections(p)

    def _find_connections(self, point):
        for conn in point.connections:
            if (conn.x, conn.y) not in self.coordinates:
                self.coordinates.add((conn.x, conn.y))
                self.points.append(conn)
                self._state = None

                if self.top.y > conn.y:
                    self.top = conn
                if self.bottom.y < conn.y:
                    self.bottom = conn
                if self.left.x > conn.x:
                    self.left = conn
                if self.right.x < conn.x:
                    self.right = conn

                self._find_connections(conn)

    def get_state(self):
        if self._state is None:
            sorted_coordinates = sorted(sorted(list(self.coordinates), key=itemgetter(1)), key=itemgetter(0))
            sorted_coord_strings = ['%s,%s' % (x, y) for x, y in sorted_coordinates]
            self._state = hashlib.md5('-'.join(sorted_coord_strings)).digest()
        return self._state

    @property
    def adjacent_points(self):
        group_and_adjacent_points = []
        for p in self.points:
            group_and_adjacent_points += p.adjacent_points

        adjacent_points = [p
                           for p in group_and_adjacent_points
                           if (p.x, p.y) not in self.coordinates]

        return adjacent_points

    @property
    def liberties(self):
        return [p
                for p in self.adjacent_points
                if not p.is_occupied]

    @property
    def capturing_color(self):
        adjacent_points = self.adjacent_points
        if not adjacent_points:
            return None

        capturing_colors = {p.color for p in adjacent_points}
        return adjacent_points[0].color if len(capturing_colors) == 1 else None

    @property
    def is_captured(self):
        return self.capturing_color is not None

    def clear(self):
        for p in self.points:
            p.clear()
