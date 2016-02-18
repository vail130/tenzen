from __future__ import absolute_import, unicode_literals, print_function

from tenzen.group import Group


class Point(object):
    def __init__(self, x, y, board):
        self.x = x
        self.y = y
        self._board = board

        self.is_occupied = False
        self.color = None
        self.territory_color = None

    def fill(self, color):
        if self.is_occupied:
            raise ValueError()

        self.is_occupied = True
        self.color = color

    def clear(self):
        if not self.is_occupied:
            raise ValueError()

        self.is_occupied = False
        self.color = None

    @property
    def adjacent_points(self):
        x, y = self.x, self.y
        potential_adjacent_points = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]

        adjacent_points = []
        for xp, yp in potential_adjacent_points:
            point = self._board.get_point(coordinates=[xp, yp])
            if point is not None:
                adjacent_points.append(point)

        return adjacent_points

    @property
    def is_captured(self):
        return all(p.is_occupied and p.color != self.color
                   for p in self.adjacent_points)

    @property
    def connections(self):
        return [p for p in self.adjacent_points if p.color == self.color]

    @property
    def liberties(self):
        return [p for p in self.adjacent_points if not p.is_occupied]

    def calculate_territory_color(self):
        if not self.is_occupied:
            self.territory_color = Group(point=self).capturing_color

    def clone(self, board):
        clone = self.__class__(self.x, self.y, board)
        clone.is_occupied = self.is_occupied
        clone.color = self.color
        clone.territory_color = self.territory_color
        return clone

    def __str__(self):
        if self.is_occupied:
            return self.color.name[0].upper()

        if self.territory_color is not None:
            return self.territory_color.name[0].lower()

        return '.'
