from __future__ import absolute_import, unicode_literals, print_function

import argparse
import re

from enum import Enum

BOARD_DIMENSION = 19
MIN_BOARD_DIMENSION = 5
MAX_BOARD_DIMENSION = 19


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
    def surrounding_points(self):
        x, y = self.x, self.y
        potential_surrounding_points = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]

        surrounding_points = []
        for xp, yp in potential_surrounding_points:
            if not (0 <= xp < len(self.board.points)):
                continue
            if not (0 <= yp < len(self.board.points[xp])):
                continue
            surrounding_points.append(self.board.points[xp][yp])

        return surrounding_points

    @property
    def is_captured(self):
        return all([p.is_occupied and p.color != self.color
                    for p in self.surrounding_points])

    @property
    def liberties(self):
        return [p for p in self.surrounding_points if not p.is_occupied]

    def __str__(self):
        # TODO: Represent territory with lowercase letter
        return self.color.name[0].upper() if self.is_occupied else '.'


class Board(object):
    def __init__(self, dimension):
        self.dimension = dimension
        self.points = [[Point(x, y, self) for y in range(dimension)] for x in range(dimension)]

    def is_complete(self):
        return all([p.is_occupied for row in self.points for p in row])

    def add_piece(self, coordinates, color):
        x, y = coordinates
        try:
            self.points[x][y].fill(color)
        except IndexError:
            raise ValueError('[%s,%s] are invalid coordinates' % (x, y))

    def remove_captured_stones(self, color):
        # TODO: Remove captured stone groups

        for row in self.points:
            for point in row:
                if point.is_occupied and point.color == color and point.is_captured:
                    point.clear()

    def __str__(self):
        transposed_points = zip(*self.points)
        a_z = [str('  ')] + [str(unichr(ord('A') + i)) for i in range(self.dimension)]
        return '\n'.join(
            [' '.join(a_z)] +
            [' '.join(
                [str(j + 1) if j + 1 > 9 else str(' %s' % (j + 1))] + [str(p) for p in row]
            ) for j, row in enumerate(transposed_points)]
        )


class Game(object):
    def __init__(self, user_color, board_dimension=BOARD_DIMENSION):
        self.user_color = getattr(Color, user_color)
        self.computer_color = Color.black if self.user_color == Color.white else Color.white
        self.board_dimension = board_dimension

        if not (MIN_BOARD_DIMENSION <= self.board_dimension <= MAX_BOARD_DIMENSION):
            raise ValueError('Board dimension must be from %s to %s.' % (MIN_BOARD_DIMENSION, MAX_BOARD_DIMENSION))

        self.turn_color = Color.black
        self.board = None
        self.last_player_passed = False

    def play(self):
        self._setup()
        self._run()
        self._end()

    def _setup(self):
        print('\n'.join([
            '',
            "Let's play! You're %s and the computer is %s on a %sx%s board." % (self.user_color.name,
                                                                                self.computer_color.name,
                                                                                self.board_dimension,
                                                                                self.board_dimension),
        ]))
        self.board = Board(dimension=self.board_dimension)

    def _run(self):
        try:
            while True:
                self._do_turn()
        except GameOver:
            pass

    def _end(self):
        # TODO
        print('\n'.join([
            '',
            'The game has ended:',
            '',
            str(self.board),
            '',
        ]))

    def _do_turn(self):
        try:
            if self.turn_color == self.user_color:
                self._place_user_stone()
            else:
                self._place_computer_stone()
        except PassTurn:
            if self.last_player_passed:
                raise GameOver()
            else:
                self.last_player_passed = True

        self._remove_opponent_captured_stones()
        self._remove_player_captured_stones()

        # TODO: Prevent previous board state

        self._change_turn()

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

                if not (1 < len(coord_str) < 4):
                    raise ValueError('Invalid input: %s' % coord_str)

                x = ord(coord_str[0]) - ord('A')
                y = int(''.join(coord_str[1:])) - 1
                self.board.add_piece(coordinates=[x, y], color=self.turn_color)
            except ValueError:
                pass
            else:
                turn_has_played = True

    def _place_computer_stone(self):
        if self.board.is_complete():
            raise PassTurn()

        # TODO: Magic
        for y in range(self.board_dimension):
            for x in range(self.board_dimension):
                try:
                    self.board.add_piece(coordinates=[x, y], color=self.turn_color)
                except ValueError:
                    pass
                else:
                    return

        raise PassTurn()

    def _remove_opponent_captured_stones(self):
        self.board.remove_captured_stones(color=self._get_opponent_color())

    def _remove_player_captured_stones(self):
        self.board.remove_captured_stones(color=self.turn_color)

    def _change_turn(self):
        self.turn_color = self._get_opponent_color()

    def _get_opponent_color(self):
        return Color.black if self.turn_color == Color.white else Color.white


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Play a game of Go.')
    parser.add_argument('-c', '--color', default='black', choices=['black', 'white'],
                        help='the color you want to be, default: black')
    parser.add_argument('-b', '--board', default=19, type=int,
                        help='dimension of the board, default: 19')

    args = parser.parse_args()

    Game(user_color=args.color, board_dimension=args.board).play()
