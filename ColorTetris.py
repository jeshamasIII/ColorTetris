from copy import deepcopy
import time
import curses
import random


class Piece:
    def __init__(self, indices, center, color):
        self.indices = indices
        self.center = center
        self.last_move_overlap = False
        self.color = color


class Board:
    def __init__(self, array_length, array_width):
        self.array_length = array_length
        self.array_width = array_width
        self.array = [[0] * self.array_width for _ in range(self.array_length)]
        self.active_piece = None

    def in_bounds(self, temp_indices):
        return all(0 <= i < self.array_length and 0 <= j < self.array_width
                   for i, j in temp_indices)

    def no_overlap(self, temp_indices):
        return all(self.array[i][j] == 0 for i, j in
                   set(temp_indices) - set(self.active_piece.indices))

    def add_piece(self, piece):
        # try to place Piece near top center of screen
        temp_indices = [(i, j + int(self.array_width / 2) - 1)
                        for i, j in piece.indices]

        if all(self.array[i][j] == 0 for i, j in temp_indices):
            self.active_piece = piece
            self.update_array(temp_indices)
            piece.indices = temp_indices
            piece.center[1] += self.array_width // 2 - 1
            piece.last_move_overlap = False
        else:
            piece.last_move_overlap = True

    def rotate(self, piece):
        # rotates Piece indices 90 degrees counter clockwise using a rotation
        # matrix
        x, y = piece.center

        temp_indices = [(int(-j + y + x), int(i - x + y))
                        for i, j in piece.indices]

        if (self.in_bounds(temp_indices)
                and self.no_overlap(temp_indices)):
            self.update_array(temp_indices)
            piece.indices = temp_indices

    def translate(self, piece, direction):
        if direction == 'right':
            x, y = 0, 1
        elif direction == 'left':
            x, y = 0, -1
        elif direction == 'down':
            x, y = 1, 0

        temp_indices = [(i + x, j + y) for i, j in piece.indices]
        if (self.in_bounds(temp_indices)
                and self.no_overlap(temp_indices)):
            self.update_array(temp_indices)

            piece.indices = temp_indices
            piece.center[0] += x
            piece.center[1] += y

            piece.last_move_overlap = False

        elif (self.in_bounds(temp_indices)
              and not self.no_overlap(temp_indices)):
            piece.last_move_overlap = True

        elif not self.in_bounds(temp_indices) and direction == 'down':
            piece.last_move_overlap = True

    def update_array(self, new_indices):
        for i, j in self.active_piece.indices:
            self.array[i][j] = 0
        for i, j in new_indices:
            self.array[i][j] = self.active_piece.color


class CursesWindow:
    def __init__(self, game):
        self.game = game
        self.window = None

    def update(self):
        pass

    def refresh(self):
        self.window.refresh()

    def addstr(self, y, x, string):
        self.window.addstr(y, x, string)


class ScoreWindow(CursesWindow):
    def __init__(self, game):
        CursesWindow.__init__(self, game)
        self.window = curses.newwin(5, 14, 0, game.board.array_width + 3)
        self.window.border('*', '*', '*', '*', '*', '*', '*', '*')
        self.update()

    def update(self):
        self.window.addstr(1, 1, f'Score:{self.game.score}')
        self.window.addstr(2, 1, f'Lines:{self.game.lines_completed}')
        self.window.addstr(3, 1, f'Level:{self.game.level}')
        self.window.refresh()


class BoardWindow(CursesWindow):
    def __init__(self, game):
        CursesWindow.__init__(self, game)
        self.window = curses.newwin(
            game.board.array_length + 2,
            game.board.array_width + 2
        )
        self.update()

    def update(self):
        self.window.border('*', '*', '*', '*', '*', '*', '*', '*')
        for i in range(self.game.board.array_length):
            for j in range(self.game.board.array_width):
                if self.game.board.array[i][j] != 0:
                    self.window.addstr(
                        i + 1,
                        j + 1,
                        '1',
                        curses.color_pair(self.game.board.array[i][j])
                    )
                else:
                    self.window.addstr(i + 1, j + 1, '.')
        self.window.refresh()

    def keypad(self, flag):
        self.window.keypad(flag)

    def nodelay(self, flag):
        self.window.nodelay(flag)

    def getch(self):
        return self.window.getch()


class PreviewWindow(CursesWindow):
    def __init__(self, game):
        CursesWindow.__init__(self, game)
        self.window = curses.newwin(6, 6, 5, game.board.array_width + 3)
        self.update()

    def update(self):
        self.window.erase()
        self.window.border('*', '*', '*', '*', '*', '*', '*', '*')
        for i in range(4):
            for j in range(4):
                if (i, j) in self.game.next_piece.indices:
                    self.window.addstr(
                        i + 1,
                        j + 1,
                        '1',
                        curses.color_pair(self.game.next_piece.color)
                    )
                # else:
                #     self.window.addstr(i + 1, j + 1, '.')

        self.window.refresh()


class GUI:
    def __init__(self, game):
        self.game = game

        curses.initscr()
        curses.start_color()

        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)

        self.board_window = BoardWindow(game)
        self.score_window = ScoreWindow(game)
        self.piece_preview_window = PreviewWindow(game)

        curses.noecho()
        curses.cbreak()
        self.board_window.keypad(True)
        self.board_window.nodelay(True)
        curses.curs_set(0)


class Game:
    SPACE_KEY = 32

    def __init__(self, board_length, board_width):
        self.board = Board(board_length, board_width)

        self.score = 0
        self.lines_completed = 0
        self.level = 0
        self.frame_rate = 60

        self.pieces = [
            Piece([(0, 1), (1, 1), (2, 1), (3, 1)], [1.5, 1.5], 1),  # I
            Piece([(0, 1), (1, 1), (2, 1), (2, 2)], [1, 1], 2),  # J
            Piece([(0, 1), (1, 1), (2, 1), (2, 0)], [1, 1], 3),  # L
            Piece([(0, 0), (0, 1), (1, 0), (1, 1)], [.5, .5], 4),  # O
            Piece([(1, 0), (1, 1), (0, 1), (0, 2)], [1, 1], 5),  # S
            Piece([(1, 0), (1, 1), (1, 2), (0, 1)], [1, 1], 6),  # T
            Piece([(0, 0), (0, 1), (1, 1), (1, 2)], [1, 1], 7)  # Z
        ]

        self.next_piece = deepcopy(random.choice(self.pieces))

        self.GUI = GUI(self)

    def points(self, number_of_lines):
        coefficients = [0, 40, 100, 300, 1200]
        return coefficients[number_of_lines] * (self.level + 1)

    def main_loop(self):
        self.board.add_piece(self.next_piece)
        self.next_piece = deepcopy(random.choice(self.pieces))
        self.GUI.piece_preview_window.update()

        loop_count = 0
        while True:
            keyboard_input = self.GUI.board_window.getch()

            loop_count += 1
            force_move = (loop_count % max(self.frame_rate - self.level, 1) == 0)
            hard_drop = (keyboard_input == self.SPACE_KEY)
            if force_move or hard_drop:
                if hard_drop:
                    while not self.board.active_piece.last_move_overlap:
                        self.board.translate(self.board.active_piece, 'down')

                    self.GUI.board_window.update()
                    time.sleep(.5)

                elif force_move:
                    self.board.translate(self.board.active_piece, 'down')

                if self.board.active_piece.last_move_overlap:
                    # clear lines one at a time starting from top of screen
                    line_count = 0
                    for row_number, row in enumerate(self.board.array):
                        if all(row):
                            line_count += 1

                            del self.board.array[row_number]
                            self.board.array.insert(0, [0] * self.board.array_width)

                            self.GUI.board_window.addstr(
                                row_number + 1, 1, '=' * self.board.array_width
                            )

                            self.GUI.board_window.refresh()
                            time.sleep(.5)

                            self.GUI.board_window.update()
                            time.sleep(.5)

                    self.score += self.points(line_count)
                    self.lines_completed += line_count
                    self.level = self.lines_completed // 2

                    self.GUI.score_window.update()

                    # try to add nextPiece to Board
                    self.board.add_piece(self.next_piece)

                    # if unsuccessful, gameover
                    if self.next_piece.last_move_overlap:
                        break

                    self.next_piece = deepcopy(random.choice(self.pieces))
                    self.GUI.piece_preview_window.update()

            else:
                if keyboard_input == ord('w'):
                    self.board.rotate(self.board.active_piece)
                if keyboard_input == ord('d'):
                    self.board.translate(self.board.active_piece, 'right')
                if keyboard_input == ord('s'):
                    self.board.translate(self.board.active_piece, 'down')
                if keyboard_input == ord('a'):
                    self.board.translate(self.board.active_piece, 'left')
                # exit game
                if keyboard_input == ord('e'):
                    break

            self.GUI.board_window.update()
            # delay after a rotation
            if keyboard_input == ord('w'):
                time.sleep(.25)

            time.sleep(1 / self.frame_rate)

        # Reset terminal window before exiting the game.
        curses.nocbreak()
        self.GUI.board_window.keypad(False)
        self.GUI.board_window.nodelay(False)
        curses.echo()
        curses.endwin()
        curses.curs_set(1)

        print('Game Over')
        exit()


def main(stdscreen):
    game = Game(16, 10)
    game.main_loop()


curses.wrapper(main)
