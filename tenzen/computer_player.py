from __future__ import absolute_import, unicode_literals, print_function

from operator import itemgetter

from tenzen.exceptions import PassTurn
from tenzen.group import Group


class ComputerPlayer(object):
    def __init__(self, board, player_color, opponent_color, invalid_moves):
        self._board = board
        self._player_color = player_color
        self._opponent_color = opponent_color
        self._invalid_moves = set(invalid_moves)

    def play(self):
        p = self.choose_point()
        self._board.add_piece(coordinates=[p.x, p.y], color=self._player_color)
        return p.x, p.y

    def choose_point(self):
        offense_value, offense_point = self.get_offensive_value_and_point()
        defense_value, defense_point = self.get_defensive_value_and_point()

        if offense_value < 0 and defense_point < 0:
            raise PassTurn()

        # Bias toward defense (establishing own territory)
        return offense_point if offense_value > defense_point else defense_point

    def get_offensive_value_and_point(self):
        opponent_groups = self._get_groups_by_color(self._opponent_color)
        capturable_groups = [self._get_capturable_group(group) for group in opponent_groups]

        # Filter out capturable_groups without liberties
        capturable_groups = [g for g in capturable_groups if g[1]]

        if not capturable_groups:
            return -1, None

        best_offensive_moves = sorted(capturable_groups, key=itemgetter(0), reverse=True)
        for value, point in best_offensive_moves:
            if (point.x, point.y) not in self._invalid_moves:
                return value, point

        return -1, None

    def get_defensive_value_and_point(self):
        num_player_stones = len([p for p in self._board.points if p.is_occupied and p.color == self._player_color])
        if num_player_stones < 5:
            z = int(round(self._board.dimension / 5.0))
            starting_points = [
                (z, z),
                (z, self._board.dimension - z),
                (self._board.dimension - z, z),
                (self._board.dimension - z, self._board.dimension - z)
            ]

            for coords in starting_points:
                p = self._board.get_point(coordinates=coords)
                if not p.is_occupied:
                    return 10, p

            for coords in starting_points:
                p = self._board.get_point(coordinates=coords)
                if not p.is_occupied and p.color == self._opponent_color:
                    adjacent_points_with_player_stone = [ap
                                                         for ap in p.adjacent_points
                                                         if ap.is_occupied and ap.color == self._player_color]
                    if not adjacent_points_with_player_stone and p.liberties:
                        return 5, p.liberties[0]

        player_groups = self._get_groups_by_color(self._player_color)
        potential_moves = [self._get_defensive_move_for_group(group) for group in player_groups]

        # Filter out potential_moves without needed points
        potential_moves = [t for t in potential_moves if t[1]]

        # TODO: Can I create any new groups to try to establish more territory?
        pass

        if not potential_moves:
            return -1, None

        best_defensive_moves = sorted(potential_moves, key=itemgetter(0), reverse=True)
        for value, point in best_defensive_moves:
            if (point.x, point.y) not in self._invalid_moves:
                return value, point

        return -1, None

    def _get_groups_by_color(self, color):
        groups = []
        covered_coordinates = set()
        for point in self._board.points:
            if point.is_occupied and point.color == color and (point.x, point.y) not in covered_coordinates:
                group = Group(points=[point])
                groups.append(group)
                covered_coordinates |= group.coordinates
        return groups

    def _get_capturable_group(self, group):
        group_liberties = group.liberties
        group_size = len(group.points)
        capture_cost = len(group_liberties)

        # TODO: Calculate the value better
        capture_value = pow(group_size, 2) / pow(capture_cost, 2) if capture_cost > 0 else 0

        # TODO: Choose liberty better and factor into value
        return capture_value, group_liberties[0]

    def _get_defensive_move_for_group(self, group):
        potential_territory = self._get_best_potential_territory_for_group(group)
        points_needed = self._get_points_needed_for_territory(potential_territory)
        if not points_needed:
            return -1, None

        territory_size = len(potential_territory)
        territory_cost = len(points_needed)

        # TODO: Calculate the value better
        territory_value = pow(territory_size, 2) / pow(territory_cost, 2) if territory_cost > 0 else 0

        # TODO: Choose point needed better and factor into value
        return territory_value, points_needed[0]

    def _get_best_potential_territory_for_group(self, group):
        potential_territory = {}

        group_width = group.right.x - group.left.x
        group_height = group.bottom.y - group.top.y
        is_horizontal_group = group_width > group_height

        if is_horizontal_group:
            # To the left of the group
            for x in range(0, group.left.x):
                for y in range(group.left.y + 1, self._board.dimension):
                    potential_territory[(x, y)] = self._board.get_point(coordinates=[x, y])

            # To the right of the group
            for x in range(group.right.x + 1, self._board.dimension):
                for y in range(group.right.y + 1, self._board.dimension):
                    potential_territory[(x, y)] = self._board.get_point(coordinates=[x, y])

            average_horizontal_position = sum(p.y for p in group.points) / len(group.points)
            if average_horizontal_position > (self._board.dimension - 1) / 2.0:
                # Under the group
                for x in range(group.left.x, group.right.x + 1):
                    y = self._board.dimension - 1
                    while (x, y) not in group.coordinates and y >= 0:
                        potential_territory[(x, y)] = self._board.get_point(coordinates=[x, y])
                        y -= 1
            else:
                # Above the group
                for x in range(group.left.x, group.right.x + 1):
                    y = 0
                    while (x, y) not in group.coordinates and y < self._board.dimension:
                        potential_territory[(x, y)] = self._board.get_point(coordinates=[x, y])
                        y += 1
        else:
            # Above the group
            for x in range(group.top.x + 1, self._board.dimension):
                for y in range(0, group.top.y):
                    potential_territory[(x, y)] = self._board.get_point(coordinates=[x, y])

            # Under the group
            for x in range(group.bottom.x + 1, self._board.dimension):
                for y in range(group.bottom.y + 1, self._board.dimension):
                    potential_territory[(x, y)] = self._board.get_point(coordinates=[x, y])

            average_horizontal_position = sum(p.x for p in group.points) / len(group.points)
            if average_horizontal_position > (self._board.dimension - 1) / 2.0:
                # To the right of the group
                for y in range(group.left.y, group.right.y + 1):
                    x = self._board.dimension - 1
                    while (x, y) not in group.coordinates and x >= 0:
                        potential_territory[(x, y)] = self._board.get_point(coordinates=[x, y])
                        x -= 1
            else:
                # To the left of the group
                for y in range(group.left.x, group.right.x + 1):
                    x = 0
                    while (x, y) not in group.coordinates and x < self._board.dimension:
                        potential_territory[(x, y)] = self._board.get_point(coordinates=[x, y])
                        x += 1

        # Narrow down potential territory based on presence of opponent
        opponent_points_in_potential_territory = [p
                                                  for p in potential_territory.values()
                                                  if p.is_occupied and p.color == self._opponent_color]

        opponent_exists_on_middle_line = False
        for p in opponent_points_in_potential_territory:
            for x, y in potential_territory.keys():
                if is_horizontal_group:
                    if p.x < (self._board.dimension - 1) / 2.0 and x <= p.x + 1:
                        del potential_territory[(x, y)]
                    elif p.x > (self._board.dimension - 1) / 2.0 and x >= p.x - 1:
                        del potential_territory[(x, y)]
                    elif (self._board.dimension - 1) / 2.0 == p.x and x in {p.x - 1, p.x, p.x + 1}:
                        opponent_exists_on_middle_line = True
                        del potential_territory[(x, y)]
                else:
                    if p.y < (self._board.dimension - 1) / 2.0 and y <= p.y + 1:
                        del potential_territory[(x, y)]
                    elif p.y > (self._board.dimension - 1) / 2.0 and y >= p.y - 1:
                        del potential_territory[(x, y)]
                    elif (self._board.dimension - 1) / 2.0 == p.y and y in {p.y - 1, p.y, p.y + 1}:
                        opponent_exists_on_middle_line = True
                        del potential_territory[(x, y)]

        if opponent_exists_on_middle_line:
            if is_horizontal_group:
                left_territory = {(x, y): v
                                  for (x, y), v in potential_territory.items()
                                  if x < (self._board.dimension - 1) / 2.0}
                right_territory = {(x, y): v
                                   for (x, y), v in potential_territory.items()
                                   if x > (self._board.dimension - 1) / 2.0}
                potential_territory = (left_territory
                                       if len(left_territory) > len(right_territory)
                                       else right_territory)
            else:
                top_territory = {(x, y): v
                                 for (x, y), v in potential_territory.items()
                                 if y < (self._board.dimension - 1) / 2.0}
                bottom_territory = {(x, y): v
                                    for (x, y), v in potential_territory.items()
                                    if y > (self._board.dimension - 1) / 2.0}
                potential_territory = (top_territory
                                       if len(top_territory) > len(bottom_territory)
                                       else bottom_territory)

        return potential_territory

    def _get_points_needed_for_territory(self, potential_territory):
        coords_needed = []

        x_sorted_coords = sorted(potential_territory.keys(), key=itemgetter(0))
        if x_sorted_coords:
            leftmost_x = x_sorted_coords[0][0]
            if leftmost_x > 0:
                coords_needed += [(x - 1, y) for (x, y) in x_sorted_coords if x == leftmost_x]

            rightmost_x = x_sorted_coords[-1][0]
            if rightmost_x < self._board.dimension - 1:
                coords_needed += [(x + 1, y) for (x, y) in x_sorted_coords if x == rightmost_x]

        y_sorted_coords = sorted(potential_territory.keys(), key=itemgetter(1))
        if y_sorted_coords:
            topmost_y = y_sorted_coords[0][1]
            if topmost_y > 0:
                coords_needed += [(x, y - 1) for (x, y) in y_sorted_coords if y == topmost_y]

            bottommost_y = y_sorted_coords[-1][1]
            if bottommost_y < self._board.dimension - 1:
                coords_needed += [(x, y + 1) for (x, y) in y_sorted_coords if y == bottommost_y]

        if not coords_needed:
            return []

        territory_group = Group(points=[self._board.get_point(coordinates=[x, y]) for x, y in coords_needed])
        return territory_group.liberties
