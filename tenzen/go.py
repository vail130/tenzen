from __future__ import absolute_import, unicode_literals, print_function

import argparse
import hashlib
import re
from operator import itemgetter

from enum import Enum

BOARD_DIMENSION = 19
MIN_BOARD_DIMENSION = 5
MAX_BOARD_DIMENSION = 19


class SuperKo(Exception):
    pass


class PassTurn(Exception):
    pass


class GameOver(Exception):
    pass


class Color(Enum):
    black = 1
    white = 2


class Point(object):
    def __init__(self, x, y, board):
        self.x = x
        self.y = y
        self.board = board

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
            if not (0 <= xp < len(self.board.points)):
                continue
            if not (0 <= yp < len(self.board.points[xp])):
                continue
            adjacent_points.append(self.board.points[xp][yp])

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


class Board(object):
    def __init__(self, dimension):
        self.dimension = dimension
        self.points = [[Point(x, y, self) for y in range(dimension)] for x in range(dimension)]

    def clone(self):
        clone = self.__class__(self.dimension)
        for row in self.points:
            for p in row:
                clone.points[p.x][p.y] = p.clone(board=clone)
        return clone

    def get_state(self):
        return hashlib.md5(str(self)).digest()

    def is_complete(self):
        return all(p.is_occupied for row in self.points for p in row)

    def add_piece(self, coordinates, color):
        x, y = coordinates
        try:
            self.points[x][y].fill(color)
        except IndexError:
            raise ValueError('[%s,%s] are invalid coordinates' % (x, y))

    def remove_captured_stones(self, color):
        self._remove_captured_groups(color)
        self._remove_captured_individuals(color)

    def _remove_captured_groups(self, color):
        covered_coordinates = set()
        for row in self.points:
            for point in row:
                if point.is_occupied and point.color == color and (point.x, point.y) not in covered_coordinates:
                    group = Group(point)
                    if group.is_captured:
                        group.clear()
                    covered_coordinates |= group.coordinates

    def _remove_captured_individuals(self, color):
        for row in self.points:
            for point in row:
                if point.is_occupied and point.color == color and point.is_captured:
                    point.clear()

    def calculate_territories(self):
        territory_counts = {
            Color.black: 0,
            Color.white: 0,
        }

        for row in self.points:
            for point in row:
                point.calculate_territory_color()
                if point.territory_color:
                    territory_counts[point.territory_color] += 1

        return territory_counts

    def __str__(self):
        transposed_points = zip(*self.points)
        a_z = ' '.join([str('  ')] + [str(unichr(ord('A') + i)) for i in range(self.dimension)])

        def format_number(n):
            return str(n) if n > 9 else str(' %s' % n)

        return '\n'.join(
            [a_z] +
            [' '.join(
                [format_number(j + 1)] + [str(p) for p in row]
            ) for j, row in enumerate(transposed_points)]
        )


class ComputerPlayer(object):
    def __init__(self, color, board, invalid_moves):
        self.color = color
        self.board = board
        self.invalid_moves = invalid_moves

    def play(self):
        if self.board.is_complete():
            raise PassTurn()

        # TODO: Magic
        for y in range(self.board.dimension):
            for x in range(self.board.dimension):
                if (x, y) not in self.invalid_moves:
                    try:
                        self.board.add_piece(coordinates=[x, y], color=self.color)
                    except ValueError:
                        pass
                    else:
                        return x, y

        raise PassTurn()


class Game(object):
    def __init__(self, board_dimension=BOARD_DIMENSION):
        self.board_dimension = board_dimension

        if not (MIN_BOARD_DIMENSION <= self.board_dimension <= MAX_BOARD_DIMENSION):
            raise ValueError('Board dimension must be from %s to %s.' % (MIN_BOARD_DIMENSION, MAX_BOARD_DIMENSION))

        self.turn_color = Color.black
        self.board = None
        self.past_boards = []
        self.board_states = set()
        self.last_player_passed = False

        self.invalid_moves = set()
        self.current_move = None

    def play(self):
        self._setup()
        self._run()
        self._end()

    def _setup(self):
        self.board = Board(dimension=self.board_dimension)

    def _run(self):
        try:
            while True:
                self._do_turn()
        except GameOver:
            pass

    def _end(self):
        territory_counts = self.board.calculate_territories()

        print('\n'.join([
            '',
            'The game has ended:',
            '',
            str(self.board),
            '',
            'Black territory: %s' % territory_counts[Color.black],
            'White territory: %s' % territory_counts[Color.white],
        ]))

        win_margin = abs(territory_counts[Color.black] - territory_counts[Color.white])
        if win_margin:
            winner_color = sorted(territory_counts.items(), key=itemgetter(1), reverse=True)[0][0]
            print('\n'.join([
                '',
                '%s wins by %s points!' % (winner_color.name.title(), win_margin),
                '',
            ]))
        else:
            print('\n'.join([
                '',
                'Black and White draw!',
                '',
            ]))

    def _do_turn(self):
        self._setup_turn()
        self._place_stone()
        self._remove_opponent_captured_stones()
        self._remove_player_captured_stones()

        try:
            self._complete_turn()
        except SuperKo:
            self.invalid_moves.add(self.current_move)
        else:
            self.invalid_moves = set()

        self.current_move = None

    def _setup_turn(self):
        self.past_boards.append(self.board.clone())

    def _place_stone(self):
        try:
            self.current_move = ComputerPlayer(self.turn_color, self.board, self.invalid_moves).play()
        except PassTurn:
            if self.last_player_passed:
                raise GameOver()
            else:
                self.last_player_passed = True

    def _remove_opponent_captured_stones(self):
        self.board.remove_captured_stones(color=self._get_opponent_color())

    def _remove_player_captured_stones(self):
        self.board.remove_captured_stones(color=self.turn_color)

    def _complete_turn(self):
        new_board_state = self.board.get_state()
        if new_board_state in self.board_states:
            self.board = self.past_boards.pop(-1)
            raise SuperKo()
        else:
            self.board_states.add(new_board_state)
            self.turn_color = self._get_opponent_color()

    def _get_opponent_color(self):
        return Color.black if self.turn_color == Color.white else Color.white


class UserGame(Game):
    def __init__(self, board_dimension=BOARD_DIMENSION, user_color='black', test_mode=False):
        super(UserGame, self).__init__(board_dimension)

        self.user_color = getattr(Color, user_color)
        self.computer_color = Color.black if self.user_color == Color.white else Color.white
        self.test_mode = test_mode

    def _setup(self):
        super(UserGame, self)._setup()
        print('\n'.join([
            '',
            "Let's play! You're %s and the computer is %s on a %sx%s board." % (self.user_color.name,
                                                                                self.computer_color.name,
                                                                                self.board_dimension,
                                                                                self.board_dimension),
        ]))

    def _place_stone(self):
        try:
            if self.turn_color == self.user_color:
                self._place_user_stone()
            else:
                self.current_move = ComputerPlayer(self.turn_color, self.board, self.invalid_moves).play()
        except PassTurn:
            if self.last_player_passed:
                raise GameOver()
            else:
                self.last_player_passed = True

    def _complete_turn(self):
        try:
            super(UserGame, self)._complete_turn()
        except SuperKo:
            if self.turn_color == self.user_color:
                print('\n'.join([
                    '',
                    'That move is invalid, because it recreates a former board state. Choose a different move.',
                    '',
                ]))
            raise

    def _place_user_stone(self):
        print('\n'.join([
            '',
            'Current board:',
            '',
            str(self.board),
            '',
            'Where do you want to place your next piece?',
            '',
        ]))

        turn_has_played = False
        while not turn_has_played:
            try:
                coord_str = raw_input('(Something like A1 or F12, or PASS to pass) > ')
                coord_str = coord_str.upper()
                coord_str = re.sub(r'[^A-Z0-9]', '', coord_str)

                if coord_str == 'PASS':
                    raise PassTurn()

                if self.test_mode and coord_str == 'END':
                    raise GameOver()

                if not (1 < len(coord_str) < 4):
                    raise ValueError('Invalid input: %s' % coord_str)

                x = ord(coord_str[0]) - ord('A')
                y = int(''.join(coord_str[1:])) - 1

                if (x, y) in self.invalid_moves:
                    raise ValueError('That move is invalid, because it recreates a former board state. '
                                     'Choose a different move.')

                self.board.add_piece(coordinates=[x, y], color=self.turn_color)
                self.current_move = (x, y)
            except ValueError:
                pass
            else:
                turn_has_played = True


class SimulatedGame(Game):
    def _do_turn(self):
        super(SimulatedGame, self)._do_turn()

        print('\n'.join([
            '',
            'Turn %s' % (len(self.past_boards) + 1),
            '',
            str(self.board),
            '',
        ]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Play a game of Go.')
    parser.add_argument('-c', '--color', default='black', choices=['black', 'white'],
                        help='the color you want to be, default: black')
    parser.add_argument('-b', '--board', default=19, type=int,
                        help='dimension of the board, default: 19')
    parser.add_argument('-s', '--simulation', action='store_const', const=True, default=False,
                        help='simulation mode, default: False')
    parser.add_argument('-t', '--test', action='store_const', const=True, default=False,
                        help='test mode, default: False')

    args = parser.parse_args()

    if args.simulation:
        SimulatedGame(board_dimension=args.board).play()
    else:
        UserGame(user_color=args.color, board_dimension=args.board, test_mode=args.test).play()
