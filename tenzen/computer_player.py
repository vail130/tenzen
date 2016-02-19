from __future__ import absolute_import, unicode_literals, print_function

import logging
import time
from operator import itemgetter

from tenzen.exceptions import PassTurn
from tenzen.group import Group

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)


class ComputerPlayer(object):
    def __init__(self, player_color, opponent_color):
        self._player_color = player_color
        self._opponent_color = opponent_color

        self._board = None
        self._past_boards = None
        self._invalid_moves = None

        self._player_groups = None
        self._territory_moves = {}
        self._opponent_groups = None
        self._capture_moves = {}

    def play(self, board, past_boards, invalid_moves):
        self._board = board
        self._past_boards = past_boards
        self._invalid_moves = set(invalid_moves)

        return self.choose_point()

    def choose_point(self):
        potential_moves = self.get_initial_moves()
        if potential_moves:
            log.debug('Initial moves exist!')

        if not potential_moves:
            potential_moves = self.get_territory_moves() + self.get_capture_moves()

        if not potential_moves:
            log.debug('Pass: No potential_moves')
            raise PassTurn()

        best_move_value = -1
        best_move_point = None

        potential_moves = sorted(potential_moves, key=itemgetter(0), reverse=True)
        for potential_move in potential_moves:
            move_value, move_point = potential_move
            if (move_point.x, move_point.y) not in self._invalid_moves:
                best_move_value, best_move_point = potential_move
                break

        if best_move_point is None or best_move_value < 0:
            log.debug('Pass: %s %s %s', self._player_color, repr(best_move_point), best_move_value)
            raise PassTurn()

        log.debug('Best Move: %s %s %s', self._player_color, repr(best_move_point), best_move_value)

        return best_move_point

    def get_initial_moves(self):
        start = time.time()

        initial_moves = []
        if len(self._past_boards) < 10:
            initial_move = self._get_initial_move()
            if initial_move[0] > 0 and initial_move[1] is not None:
                initial_moves.append(initial_move)

        end = time.time()
        log.debug('get_initial_moves took %s', (end - start))
        return initial_moves

    def get_territory_moves(self):
        start = time.time()

        self._player_groups, updated = self._update_groups(self._player_groups, self._player_color)
        if updated:
            self._update_moves(self._player_groups, self._territory_moves, self._get_defensive_move_for_group)

        end = time.time()
        log.debug('get_territory_moves took %s', (end - start))
        return self._territory_moves.values()

    def get_capture_moves(self):
        start = time.time()

        self._opponent_groups, updated = self._update_groups(self._opponent_groups, self._opponent_color)
        if updated:
            self._update_moves(self._opponent_groups, self._capture_moves, self._get_capturable_group)

        end = time.time()

        log.debug('get_capture_moves took %s', (end - start))
        return self._capture_moves.values()

    def _get_initial_move(self):
        z = int(round(self._board.dimension / 5.0))
        starting_points = [
            (z - 1, z - 1),
            (z - 1, self._board.dimension - z),
            (self._board.dimension - z, z - 1),
            (self._board.dimension - z, self._board.dimension - z)
        ]

        for coords in starting_points:
            p = self._board.get_point(coordinates=coords)
            if not p.is_occupied:
                return 10, p

        for coords in starting_points:
            p = self._board.get_point(coordinates=coords)
            if p.is_occupied and p.color == self._opponent_color:
                adjacent_points_with_player_stone = [ap
                                                     for ap in p.adjacent_points
                                                     if ap.is_occupied and ap.color == self._player_color]
                liberties = p.liberties
                if not adjacent_points_with_player_stone and liberties:
                    for liberty_point in liberties:
                        # TODO: Choose liberty closer to walls
                        if (liberty_point.x, liberty_point.y) not in self._invalid_moves:
                            return 10, liberty_point

        return -1, None

    def _update_groups(self, groups, color):
        if groups is None:
            groups = self._get_groups_by_color(color)
            return groups, True
        else:
            return self._get_updated_groups(groups, color)

    @staticmethod
    def _update_moves(groups, moves_dict, move_function):
        existing_states = set(moves_dict.keys())

        updated_group_states = set()
        for group in groups:
            group_state = group.get_state()
            updated_group_states.add(group_state)

            if group_state not in moves_dict:
                move = move_function(group)
                if move[1] is not None:
                    moves_dict[group_state] = move
            else:
                existing_states.remove(group_state)

        for group_state in existing_states:
            del moves_dict[group_state]

    def _get_groups_by_color(self, color):
        groups = []
        covered_coordinates = set()
        for point in self._board.points:
            if point.is_occupied and point.color == color and (point.x, point.y) not in covered_coordinates:
                group = Group(points=[point])
                groups.append(group)
                covered_coordinates |= group.coordinates
        return groups

    def _get_updated_groups(self, groups, color):
        previous_board = self._past_boards[-1]
        changed_coords = {(p.x, p.y)
                          for p in self._board.points
                          if previous_board.get_point(coordinates=[p.x, p.y]) != p}

        all_group_coords = set()
        captured_group_indices = set()
        updated_group_indices = set()
        for i, group in enumerate(groups):
            all_group_coords |= group.coordinates
            group_changed_coords = group.coordinates & changed_coords
            group_was_captured = len(group_changed_coords) == len(group.points)
            if group_was_captured:
                captured_group_indices.add(i)
            elif group_changed_coords:
                updated_group_indices.add(i)

        new_groups = []
        covered_coordinates = set(all_group_coords)
        for point in self._board.points:
            if point.is_occupied and point.color == color and (point.x, point.y) not in covered_coordinates:
                group = Group(points=[point])
                new_groups.append(group)
                covered_coordinates |= group.coordinates

        if not captured_group_indices and not updated_group_indices and not new_groups:
            log.debug('No captured, changed or created groups with color %s', color)
            return groups, False

        updated_groups = []
        if new_groups:
            log.debug('New groups added!')
            updated_groups += new_groups

        if captured_group_indices or updated_group_indices:
            log.debug('Groups captured/changed!')
            for i, group in enumerate(groups):
                if i not in captured_group_indices and i not in updated_group_indices:
                    updated_groups.append(group)
                elif i in updated_group_indices:
                    covered_coordinates = set()
                    for point in group.points:
                        if point.is_occupied and point.color == color and (point.x, point.y) not in covered_coordinates:
                            group = Group(points=[point])
                            groups.append(group)
                            covered_coordinates |= group.coordinates
                            updated_groups.append(group)

        return updated_groups, True

    def _get_capturable_group(self, group):
        group_liberties = group.liberties
        group_size = len(group.points)
        capture_cost = len(group_liberties)

        occupied_points = [1 for p in self._board.points if p.is_occupied]
        percent_board_filled = float(sum(occupied_points)) / float(len(occupied_points)) if len(
            occupied_points) > 0 else 0

        # TODO: Calculate the value better
        capture_value = float(group_size) / float(
            pow(capture_cost, 2)) * percent_board_filled if capture_cost > 0 else 0

        # TODO: Choose liberty better and factor into value
        return capture_value, group_liberties[0]

    def _get_defensive_move_for_group(self, group):
        potential_territory = self._get_best_potential_territory_for_group(group)
        points_needed = self._get_points_needed_for_territory(potential_territory)
        if not points_needed:
            return -1, None

        territory_size = len(potential_territory)

        occupied_points = [1 for p in self._board.points if p.is_occupied]
        percent_board_filled = float(sum(occupied_points)) / float(len(occupied_points)) if len(
            occupied_points) > 0 else 0

        # TODO: Calculate the value better
        territory_value = (float(territory_size) / percent_board_filled
                           if percent_board_filled > 0
                           else float(territory_size))

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

        territory_group = Group(points=[self._board.get_point(coordinates=[x, y]) for x, y in coords_needed],
                                auto_find=False)
        return territory_group.liberties
