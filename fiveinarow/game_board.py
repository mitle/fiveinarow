# -*- coding: utf-8 -*-

"""
Five in a row game board, grid drawer based on pygame
"""

import logging
import pygame
import numpy as np
from functools import reduce
import time

class Board:
    class OccupiedException(Exception):
        pass

    def __init__(self, shape, num_to_win):
        """
        Initialising the board with its size, number of moves in a row.
        :param shape: board size value-pair, tuple
        :param num_to_win: number of moves in a row to win
        """
        self.size = shape
        self.board = np.zeros(self.size)  # Using a numpy array, indexable with a coordinate pair
        if max(self.size) < num_to_win:
            self.num_to_win = max(self.size)
            logging.info("num to win decreased to {}".format(self.num_to_win))
        else:
            self.num_to_win = num_to_win

        self.last_move = None
        self.occupied = set()
        self.gridcoord = None

    def place(self, pos, player_id):
        if not self.is_occupied(pos):
            self.board[pos] = player_id
            self.occupied.add(pos)
            self.last_move = (pos, player_id)
        else:
            raise self.OccupiedException

    def clear(self):
        self.board = np.zeros(self.size)
        self.occupied = set()

    def __is_in_grid(self, pos):
        x, y = pos
        if x < 0 or self.size[0] <= x:
            return False
        if y < 0 or self.size[1] <= y:
            return False

        return True

    def get_occupied(self):
        return self.occupied

    def is_occupied(self, pos):
        return pos in self.occupied

    def get_player_id(self, pos):
        return int(self.board[pos])

    def __check_row(self, origin, direction):
        to_count = self.num_to_win

        player_id = origin[1]

        count_minus_dir = 0
        pos = origin[0]
        while True:
            pos = tuple(map(lambda p, d: (p - d), pos, direction))
            if not self.__is_in_grid(pos):
                break
            if not self.is_occupied(pos):
                break
            if self.get_player_id(pos) == player_id:
                count_minus_dir += 1

        count_plus_dir = 0
        pos = origin[0]
        while True:
            pos = tuple(map(lambda p, d: (p + d), pos, direction))
            if not self.__is_in_grid(pos):
                break
            if not self.is_occupied(pos):
                break
            if self.get_player_id(pos) == player_id:
                count_plus_dir += 1

        if to_count <= count_plus_dir + count_minus_dir + 1:  # origin is not counted by the methods above
            return True
        else:
            return False

    def check_board(self):
        origin = self.last_move

        if len(self.occupied) == reduce(lambda x, y: x * y, self.size):
            logging.info("board is full")
            return origin, (0, 0)

        directions = [(1, 0), (1, 1), (0, 1), (-1, 1)]
        for d in directions:
            if self.__check_row(origin, d):
                return origin, d

        return None


class Grid:
    def __init__(self, screen, clock, conf):
        self.screen = screen
        self.clock = clock
        self.conf = conf
        self.__update_conf()
        self.anim_speed = 20
        self.board = Board((self.cols, self.rows), conf['n_to_win'])
        self.gridcoord = None

    def set_anim_speed(self, speed):
        self.anim_speed = speed

    def __update_conf(self):
        self.gridcolor = self.conf['gridcolor']
        self.cols = self.conf['numgridx']
        self.rows = self.conf['numgridy']
        self.bold_grid = self.conf['bold_grid']
        self.colors = self.conf['player_colors']

        xboundary = 30
        yboundary = 30
        screen_width, screen_height = self.screen.get_size()

        grid_bbh = screen_height - 2 * yboundary  # grid Bounding Box Height
        grid_bbw = screen_width - 2 * xboundary

        self.squaresize = min((grid_bbw / self.cols, grid_bbh / self.rows))

        # tries to fit grid at best in the window
        if self.cols / self.rows > 1:
            if grid_bbw / grid_bbh > 1:
                if self.cols / self.rows > grid_bbw / grid_bbh:
                    self.grid_offset = (0, (grid_bbh - self.rows * self.squaresize) / 2)
                else:
                    self.grid_offset = ((grid_bbw - self.cols * self.squaresize) / 2, 0)
            elif grid_bbw / grid_bbh < 1:
                self.grid_offset = (0, (grid_bbh - grid_bbw + (self.cols - self.rows) * self.squaresize) / 2)
            else:
                self.grid_offset = (0, (self.cols - self.rows) * self.squaresize / 2)

        elif self.cols / self.rows < 1:
            if grid_bbw / grid_bbh > 1:
                self.grid_offset = ((grid_bbw - grid_bbh + (self.rows - self.cols) * self.squaresize) / 2, 0)
            elif grid_bbw / grid_bbh < 1:
                if self.cols / self.rows > grid_bbw / grid_bbh:
                    self.grid_offset = (0, (grid_bbh - self.rows * self.squaresize) / 2)
                else:
                    self.grid_offset = ((grid_bbw - self.cols * self.squaresize) / 2, 0)
            else:
                self.grid_offset = ((self.rows - self.cols) * self.squaresize / 2, 0)

        else:
            if grid_bbw / grid_bbh > 1:
                self.grid_offset = ((grid_bbw - grid_bbh) / 2, 0)
            elif grid_bbw / grid_bbh < 1:
                self.grid_offset = (0, (grid_bbh - grid_bbw) / 2)
            else:
                self.grid_offset = (0, 0)

        self.width = 2 if self.bold_grid else 1

        grid_height = self.squaresize * self.rows
        grid_width = self.squaresize * self.cols

        self.grid_size = (grid_width, grid_height)

        self.grid_rect = (xboundary + self.grid_offset[0], yboundary + self.grid_offset[1],
                          xboundary + self.grid_offset[0] + grid_width, yboundary + self.grid_offset[1] + grid_height)

    def draw_grid(self, flush=False, animate=False):
        """
        Draws the game grid from individual lines.
        :param flush: whether update the screen at end
        :param animate: whwther update screen after each drawn line
        :return: None
        """

        for r in range(self.rows + 1):
            pos_y = self.squaresize * r + self.grid_rect[1]

            pos_x_start = self.grid_rect[0]
            pos_x_end = self.grid_rect[2]

            x = pygame.draw.line(self.screen, self.gridcolor, (pos_x_start, pos_y), (pos_x_end, pos_y), self.width)
            if animate:
                pygame.display.update(x)
                self.clock.tick(self.anim_speed)

        for c in range(self.cols + 1):
            pos_x = self.squaresize * c + self.grid_rect[0]

            pos_y_start = self.grid_rect[1]
            pos_y_end = self.grid_rect[3]

            x = pygame.draw.line(self.screen, self.gridcolor, (pos_x, pos_y_start), (pos_x, pos_y_end), self.width)
            if animate:
                pygame.display.update(x)
                self.clock.tick(self.anim_speed)

        if flush:
            pygame.display.update()

    def process_event(self, event):
        """
        Processes event for grid click, stores click coordinates
        :param event: pygame event
        :return: None
        """

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.gridcoord = self.get_clicked_cell(event.pos)

    def get_clicked_cell(self, event_pos):
        """
        Calculates grid coorfinates from window coordinates
        :param event_pos: position tuple of the mouse click
        :return: grid coordinates if click was over the grid else None
        """

        posx = event_pos[0] - self.grid_rect[0]
        posy = event_pos[1] - self.grid_rect[1]

        if posx < 0 or self.grid_size[0] < posx:
            return None
        if posy < 0 or self.grid_size[1] < posy:
            return None

        x = int(posx / self.squaresize)
        y = int(posy / self.squaresize)

        return x, y

    def get_gridcoord(self):
        return self.gridcoord

    def clear_gridcoord(self):
        self.gridcoord = None

    def draw_board(self):
        """
        Draws all the players previous moves on the screen
        :return: None
        """

        for pos in self.board.get_occupied():
            player_id = self.board.get_player_id(pos)
            self.__draw_move(pos, player_id)


    def __draw_move(self, pos, player_id):
        """
        Draws a single moves marker
        :param pos:  grid coordinates
        :param player_id: player id for color lookup
        :return: None
        """

        pos_x = int(self.grid_rect[0] + pos[0] * self.squaresize + self.squaresize/2)
        pos_y = int(self.grid_rect[1] + pos[1] * self.squaresize + self.squaresize/2)
        markersize = int((self.squaresize*0.7)/2 )

        color = self.colors[player_id]
        pygame.draw.circle(self.screen, color, (pos_x, pos_y), markersize)


    def place(self, gridpos, player_id):
        try:
            self.board.place(gridpos, player_id)
        except self.board.OccupiedException as e:
            return True, None, False
        board_status = self.board.check_board()
        if board_status is not None:
            if board_status[1] != (0,0):  # board is full
                print("winning move ((x,y),id)={pos} in direction {dir}".format(pos=board_status[0], dir=board_status[1]))
            return False, board_status, True
            # game over

        return True, None, True


class Player:
    def __init__(self, name, id, turn):
        self.name = name
        self.id = id
        self.turn = turn
        self.points = 0
        self.last_move = None

    def wins(self):
        self.points += 1

