from __future__ import absolute_import, unicode_literals, print_function

from tenzen.exceptions import PassTurn


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
