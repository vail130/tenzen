from __future__ import absolute_import, unicode_literals, print_function


class Group(object):
    def __init__(self, point):
        self.points = [point]
        self.color = point.color
        self.coordinates = {(point.x, point.y)}

        for p in self.points:
            self._find_connections(p)

    def _find_connections(self, point):
        for conn in point.connections:
            if (conn.x, conn.y) not in self.coordinates:
                self.coordinates.add((conn.x, conn.y))
                self.points.append(conn)
                self._find_connections(conn)

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
