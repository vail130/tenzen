from __future__ import absolute_import, unicode_literals, print_function

import argparse
import re
from datetime import datetime
from operator import itemgetter

from tenzen.board import Board
from tenzen.colors import Color
from tenzen.computer_player import ComputerPlayer
from tenzen.constants import BOARD_DIMENSION, MIN_BOARD_DIMENSION, MAX_BOARD_DIMENSION
from tenzen.exceptions import SuperKo, PassTurn, GameOver


class BaseGame(object):
    def __init__(self, board_dimension=BOARD_DIMENSION):
        self.board_dimension = board_dimension

        if not (MIN_BOARD_DIMENSION <= self.board_dimension <= MAX_BOARD_DIMENSION):
            raise ValueError('Board dimension must be from %s to %s.' % (MIN_BOARD_DIMENSION, MAX_BOARD_DIMENSION))

        self.turn_color = Color.black
        self.board = None
        self.backup_board = None
        self.past_boards = tuple()
        self.board_states = set()
        self.last_player_passed = False

        self.invalid_moves = set()
        self.current_move = None

        self.start_time = None
        self.end_time = None

    def play(self):
        self._setup()
        self._run()
        self._end()

    def _setup(self):
        self.start_time = datetime.now()
        self.board = Board(dimension=self.board_dimension)
        self.players = {
            Color.black: ComputerPlayer(player_color=Color.black, opponent_color=Color.white),
            Color.white: ComputerPlayer(player_color=Color.white, opponent_color=Color.black),
        }

    def _run(self):
        try:
            while True:
                self._do_turn()
        except GameOver:
            pass

    def _end(self):
        territory_counts = self.board.calculate_territories()

        self.end_time = datetime.now()

        print('\n'.join([
            '',
            'The game has ended:',
            'Start: %s' % self.start_time,
            'End: %s' % self.end_time,
            'Duration: %s' % (self.end_time - self.start_time),
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
        self.backup_board = self.board.clone()

    def _place_stone(self):
        try:
            point = self.players[self.turn_color].play(board=self.board,
                                                       past_boards=self.past_boards,
                                                       invalid_moves=tuple(self.invalid_moves))
            coords = (point.x, point.y)
            self.board.add_piece(coordinates=coords, color=self.turn_color)
            self.current_move = coords
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
            self.board = self.backup_board
            self.backup_board = None
            raise SuperKo()
        else:
            self.board_states.add(new_board_state)
            self.backup_board = None

            past_boards = list(self.past_boards)
            past_boards.append(self.board.clone())
            self.past_boards = tuple(past_boards)

            self.turn_color = self._get_opponent_color()

    def _get_opponent_color(self):
        return Color.black if self.turn_color == Color.white else Color.white


class SimulatedGame(BaseGame):
    def _do_turn(self):
        super(SimulatedGame, self)._do_turn()

        print('\n'.join([
            '',
            'Turn %s' % len(self.past_boards),
            '',
            str(self.board),
            '',
        ]))


class UserGame(BaseGame):
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
                point = self.players[self.turn_color].play(board=self.board,
                                                           past_boards=self.past_boards,
                                                           invalid_moves=tuple(self.invalid_moves))
                coords = (point.x, point.y)
                self.board.add_piece(coordinates=coords, color=self.turn_color)
                self.current_move = coords
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
