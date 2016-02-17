from __future__ import absolute_import, unicode_literals, print_function

import argparse

import re
from enum import Enum

BOARD_DIMENSION = 19
MIN_BOARD_DIMENSION = 5
MAX_BOARD_DIMENSION = 19


class Color(Enum):
    black = 1
    white = 2


class Point(object):
    def __init__(self):
        self.is_occupied = False
        self.color = None

    def fill(self, color):
        if self.is_occupied:
            raise ValueError()

        self.is_occupied = True
        self.color = color

    def __str__(self):
        if self.is_occupied:
            return 'b' if self.color == Color.black else 'w'

        return '.'


class Board(object):
    def __init__(self, dimension):
        self.dimension = dimension
        self.points = [[Point() for _ in range(dimension)] for _ in range(dimension)]

    def is_complete(self):
        return all([p.is_occupied for row in self.points for p in row])

    def add_piece(self, coordinates, color):
        x, y = coordinates
        self.points[x][y].fill(color)

    def __str__(self):
        transposed_points = zip(*self.points)
        a_z = [str('  ')] + [str(unichr(ord('A') + i)) for i in range(self.dimension)]
        return '\n'.join(
            [' '.join(a_z)] +
            [' '.join(
                [str(j+1) if j+1 > 9 else str(' %s' % (j+1))] + [str(p) for p in row]
            ) for j, row in enumerate(transposed_points)]
        )


class Game(object):
    def __init__(self, user_color, board_dimension=BOARD_DIMENSION):
        self.user_color = getattr(Color, user_color)
        self.computer_color = Color.black if self.user_color == Color.white else Color.white
        self.board_dimension = board_dimension

        if self.board_dimension < MIN_BOARD_DIMENSION or self.board_dimension > MAX_BOARD_DIMENSION:
            raise ValueError('Board dimension must be from 5 to 19.')

        self.turn = Color.black
        self.board = None

    def play(self):
        self._setup()
        self._run()

    def _setup(self):
        print("Let's play! User is %s and computer is %s on a %sx%s board." % (self.user_color.name,
                                                                               self.computer_color.name,
                                                                               self.board_dimension,
                                                                               self.board_dimension))
        self.board = Board(dimension=self.board_dimension)

    def _run(self):
        while not self.board.is_complete():
            self._do_turn()

    def _do_turn(self):
        if self.turn == self.user_color:
            self._do_user_turn()
        else:
            self._do_computer_turn()
        self._change_turn()

    def _do_user_turn(self):
        print('\n'.join([
            '',
            'Current board:',
            '',
            str(self.board),
            '',
            'Where do you want to place your next piece?',
            '',
        ]))

        coord_str = raw_input('(Something like A1 or F12) > ')
        coord_str = coord_str.upper()
        coord_str = re.sub(r'[^A-Z0-9]', '', coord_str)

        if len(coord_str) < 2 or len(coord_str) > 3:
            raise ValueError('Invalid input')

        coordinates = [ord(coord_str[0]) - ord('A'), int(''.join(coord_str[1:])) - 1]
        self.board.add_piece(coordinates=coordinates, color=self.turn)

    def _do_computer_turn(self):
        for y in range(self.board_dimension):
            for x in range(self.board_dimension):
                try:
                    self.board.add_piece(coordinates=[x, y], color=self.turn)
                except ValueError:
                    pass
                else:
                    return

    def _change_turn(self):
        self.turn = Color.black if self.turn == Color.white else Color.white


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Play a game of Go.')
    parser.add_argument('-c', '--color', default='black', choices=['black', 'white'],
                        help='the color you want to be, default: black')
    parser.add_argument('-b', '--board', default=19, type=int,
                        help='dimension of the board, default: 19')

    args = parser.parse_args()

    Game(user_color=args.color, board_dimension=args.board).play()
