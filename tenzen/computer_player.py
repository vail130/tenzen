from __future__ import absolute_import, unicode_literals, print_function

import random

from tenzen.exceptions import PassTurn


class ComputerPlayer(object):
    def __init__(self, color, board, invalid_moves):
        self._color = color
        self._board = board
        self._invalid_moves = set(invalid_moves)

    def play(self):
        if self._board.is_complete():
            raise PassTurn()

        possible_moves = set()
        for y in range(self._board.dimension):
            for x in range(self._board.dimension):
                if (x, y) not in self._invalid_moves:
                    possible_moves.add((x, y))

        while possible_moves:
            x, y = random.choice(list(possible_moves))
            try:
                self._board.add_piece(coordinates=[x, y], color=self._color)
            except ValueError:
                possible_moves.remove((x, y))
            else:
                return x, y

        raise PassTurn()
