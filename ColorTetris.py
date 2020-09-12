from copy import deepcopy
import time
import curses
import random


class TetrisPiece:
    def __init__(self, indices, center_of_rotation, color):
        self.indices = indices
        self.center_of_rotation = center_of_rotation
        self.last_move_overlap = False
        self.color = color


class TetrisBoard:
    def __init__(self, num_rows, num_columns):
        self.num_rows = num_rows
        self.num_columns = num_columns

        self.array = [[0] * self.num_columns for _ in range(self.num_rows)]
        self.active_piece = None

    def in_bounds(self, temp_active_piece_indices):
        return all(0 <= i < self.num_rows and 0 <= j < self.num_columns
                   for i, j in temp_active_piece_indices)

    def no_overlap(self, temp_active_piece_indices):
        return all(self.array[i][j] == 0 for i, j in
                   set(temp_active_piece_indices) - set(self.active_piece.indices))

    def add_piece(self, piece):
        # try to place Piece near top center of board
        new_active_piece_indices = [(i, j + int(self.num_columns / 2) - 1)
                                    for i, j in piece.indices]

        if all(self.array[i][j] == 0 for i, j in new_active_piece_indices):
            self.active_piece = piece
            self.update_array(new_active_piece_indices)
            piece.indices = new_active_piece_indices
            piece.center_of_rotation[1] += self.num_columns // 2 - 1
            piece.last_move_overlap = False
        else:
            piece.last_move_overlap = True

    def rotate_active_piece(self):
        # rotates active piece indices 90 degrees counter clockwise about it's
        # center of a rotation

        x, y = self.active_piece.center_of_rotation

        # this translates the active piece so that it's center is now
        # the origin, then rotates each point in indices about the origin,
        # then translates the piece so that it's center is at it's
        # original position
        temp_active_piece_indices = [(int(-j + y + x), int(i - x + y))
                                     for i, j in self.active_piece.indices]

        if (self.in_bounds(temp_active_piece_indices)
                and self.no_overlap(temp_active_piece_indices)):
            self.update_array(temp_active_piece_indices)
            self.active_piece.indices = temp_active_piece_indices

    def translate_active_piece(self, direction):
        if direction == 'right':
            x, y = 0, 1
        elif direction == 'left':
            x, y = 0, -1
        elif direction == 'down':
            x, y = 1, 0

        temp_active_piece_indices = [(i + x, j + y)
                                     for i, j in self.active_piece.indices]
        if (self.in_bounds(temp_active_piece_indices)
                and self.no_overlap(temp_active_piece_indices)):
            self.update_array(temp_active_piece_indices)
            self.active_piece.indices = temp_active_piece_indices
            self.active_piece.center_of_rotation[0] += x
            self.active_piece.center_of_rotation[1] += y

            self.active_piece.last_move_overlap = False

        elif (self.in_bounds(temp_active_piece_indices)
              and not self.no_overlap(temp_active_piece_indices)):
            self.active_piece.last_move_overlap = True

        # this is necessary to tell when a piece hits the the bottom of the
        # board
        elif not self.in_bounds(temp_active_piece_indices) and direction == 'down':
            self.active_piece.last_move_overlap = True

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


class BoardWindow(CursesWindow):
    def __init__(self, game):
        CursesWindow.__init__(self, game)

        # the window's border adds two extra rows and two extra columns
        self.num_rows = game.board.num_rows + 2
        self.num_columns = game.board.num_columns + 2

        self.window = curses.newwin(
            self.num_rows,
            self.num_columns
        )

        self.window.border('*', '*', '*', '*', '*', '*', '*', '*')
        self.update()

    def update(self):
        # only update the interior of the window
        for i in range(self.num_rows - 2):
            for j in range(self.num_columns - 2):
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


class ScoreWindow(CursesWindow):
    def __init__(self, game, board_window):
        CursesWindow.__init__(self, game)
        self.num_items_to_display = 3

        # the window's border adds two extra rows
        self.num_rows = self.num_items_to_display + 2

        # this is somewhat arbitrary
        self.num_columns = 14

        self.window = curses.newwin(
            self.num_rows,
            self.num_columns,
            0,
            board_window.num_columns + 1
        )

        self.window.border('*', '*', '*', '*', '*', '*', '*', '*')
        self.update()

    def update(self):
        self.window.addstr(1, 1, f'Score:{self.game.score}')
        self.window.addstr(2, 1, f'Lines:{self.game.lines_completed}')
        self.window.addstr(3, 1, f'Level:{self.game.level}')
        self.window.refresh()


class PiecePreviewWindow(CursesWindow):
    def __init__(self, game, board_window, score_window):
        CursesWindow.__init__(self, game)

        # the window's border adds two extra rows and two extra columns
        self.num_rows = game.max_piece_length + 2
        self.num_columns = game.max_piece_length + 2

        self.window = curses.newwin(
            self.num_rows,
            self.num_columns,
            score_window.num_rows,
            board_window.num_columns + 1
        )

        self.update()

    def update(self):
        self.window.erase()
        self.window.border('*', '*', '*', '*', '*', '*', '*', '*')

        # only update the interior of the window
        for i in range(self.num_rows - 2):
            for j in range(self.num_columns - 2):
                if (i, j) in self.game.next_piece.indices:
                    self.window.addstr(
                        i + 1,
                        j + 1,
                        '1',
                        curses.color_pair(self.game.next_piece.color)
                    )

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
        self.score_window = ScoreWindow(game, self.board_window)
        self.piece_preview_window = PiecePreviewWindow(game, self.board_window,
                                                       self.score_window)

        curses.noecho()
        curses.cbreak()
        self.board_window.keypad(True)
        self.board_window.nodelay(True)
        curses.curs_set(0)


class Game:
    def __init__(self, board_num_rows, board_num_columns):
        self.board = TetrisBoard(board_num_rows, board_num_columns)

        self.score = 0
        self.lines_completed = 0
        self.level = 0

        self.SPACE_KEY_ASCII_VALUE = 32

        # approximate frame rate
        self.frame_rate = 60

        self.pieces = [
            TetrisPiece([(0, 1), (1, 1), (2, 1), (3, 1)], [1.5, 1.5], 1),  # I
            TetrisPiece([(0, 1), (1, 1), (2, 1), (2, 2)], [1, 1], 2),  # J
            TetrisPiece([(0, 1), (1, 1), (2, 1), (2, 0)], [1, 1], 3),  # L
            TetrisPiece([(0, 0), (0, 1), (1, 0), (1, 1)], [.5, .5], 4),  # O
            TetrisPiece([(1, 0), (1, 1), (0, 1), (0, 2)], [1, 1], 5),  # S
            TetrisPiece([(1, 0), (1, 1), (1, 2), (0, 1)], [1, 1], 6),  # T
            TetrisPiece([(0, 0), (0, 1), (1, 1), (1, 2)], [1, 1], 7)  # Z
        ]

        self.max_piece_length = 4

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
            hard_drop = (keyboard_input == self.SPACE_KEY_ASCII_VALUE)
            if force_move or hard_drop:
                if hard_drop:
                    while not self.board.active_piece.last_move_overlap:
                        self.board.translate_active_piece('down')

                    self.GUI.board_window.update()
                    time.sleep(.5)

                elif force_move:
                    self.board.translate_active_piece('down')

                if self.board.active_piece.last_move_overlap:
                    # try to clear lines one at a time starting from the top of
                    # the screen
                    line_count = 0
                    for row_number, row in enumerate(self.board.array):
                        if all(row):
                            # highlight row to be deleted
                            # add 1 to row_number because of board_window's border
                            self.GUI.board_window.addstr(
                                row_number + 1, 1, '=' * self.board.num_columns
                            )

                            self.GUI.board_window.refresh()
                            time.sleep(.5)

                            # delete row
                            del self.board.array[row_number]
                            self.board.array.insert(0, [0] * self.board.num_columns)

                            self.GUI.board_window.update()
                            time.sleep(.5)

                            line_count += 1

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
                    self.board.rotate_active_piece()
                if keyboard_input == ord('d'):
                    self.board.translate_active_piece('right')
                if keyboard_input == ord('s'):
                    self.board.translate_active_piece('down')
                if keyboard_input == ord('a'):
                    self.board.translate_active_piece('left')
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


# Run the game
game = Game(board_num_rows=16, board_num_columns=10)
game.main_loop()
