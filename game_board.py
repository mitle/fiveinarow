#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game board, grid drawer based on pygame
"""

import pygame
import numpy as np
import time

class Board:
    class OccupiedException(Exception):
        pass

    def __init__(self, shape, num_to_win):
        self.size = shape
        self.board = np.zeros(self.size)
        self.num_to_win = num_to_win
        self.last_move = None
        self.occupied = set()
        self.gridcoord = None

    def place(self, pos, color):
        if pos not in self.occupied:
            self.board[pos] = color
            self.occupied.add(pos)
            self.last_move = (pos, color)
        else:
            raise self.OccupiedException

    def __is_in_grid(self, pos):
        x, y = pos
        if x < 0 or self.size[0] <= x:
            return False
        if y < 0 or self.size[1] <= y:
            return False

        return True

    def get_occupied(self):
        return self.occupied

    def get_color(self, pos):
        return self.board[pos]

    def __check_row(self, origin, direction):
        to_count = self.num_to_win

        color = origin[1]

        count_minus_dir = 0
        pos = origin[0]
        while self.get_color(pos) == color:
            pos = tuple(map(lambda p, d: (p - d), pos, direction))
            count_minus_dir += 1

        count_plus_dir = 0
        pos = origin[0]
        while self.get_color(pos) == color:
            pos = tuple(map(lambda p, d: (p + d), pos, direction))
            count_plus_dir += 1

        if to_count == count_plus_dir + count_minus_dir - 1: ## origin is counted twice
            return True
        else:
            return False

    def check_board(self):
        origin = self.last_move
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
        self.colors = {1: (255, 0, 0), 2: (0, 0, 0)}

        self.xboundary = 30
        self.yboundary = 30
        screen_width, screen_height = self.screen.get_size()
        self.grid_height = screen_height - 2 * self.yboundary
        self.grid_width = screen_width - 2 * self.xboundary

        if self.grid_width < self.grid_height:
            self.yboundary += (screen_height - screen_width) / 2
            self.grid_height = self.grid_width

        elif self.grid_width > screen_height:
            self.xboundary += (screen_width - screen_height) / 2
            self.grid_width = self.grid_height

        self.width = 2 if self.bold_grid else 1

        self.squaresize = self.grid_width / self.cols

    def draw_grid(self, flush=False, animate=False):
        screen_width, screen_height = self.screen.get_size()
        for r in range(self.rows + 1):
            pos_y = (self.grid_height / self.rows) * r + self.yboundary
            pos_x_start = self.xboundary
            pos_x_end = screen_width - self.xboundary
            pygame.draw.line(self.screen, self.gridcolor, (pos_x_start, pos_y), (pos_x_end, pos_y), self.width)
            if animate:
                pygame.display.flip()
                self.clock.tick(self.anim_speed)
        for c in range(self.cols + 1):
            pos_x = (self.grid_width / self.cols) * c + self.xboundary
            pos_y_start = self.yboundary
            pos_y_end = screen_height - self.yboundary
            pygame.draw.line(self.screen, self.gridcolor, (pos_x, pos_y_start), (pos_x, pos_y_end), self.width)
            if animate:
                pygame.display.flip()
                self.clock.tick(self.anim_speed)

        if flush:
            pygame.display.flip()

    def process_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.gridcoord = self.get_clicked_cell(event.pos)

    def get_clicked_cell(self, event_pos):
        posx = event_pos[0] - self.xboundary
        posy = event_pos[1] - self.yboundary

        if posx < 0 or self.grid_width < posx:
            return
        if posy < 0 or self.grid_height < posy:
            return

        x = int(posx / self.squaresize)
        y = int(posy / self.squaresize)

        return x, y

    def get_gridcoord(self):
        return self.gridcoord

    def clear_gridcoord(self):
        self.gridcoord = None

    def draw_board(self):
        for pos in self.board.get_occupied():
            playercolor = self.board.get_color(pos)
            self.__draw_move(pos, playercolor)


    def __draw_move(self, pos, playercolor):
        pos_x = int(self.xboundary + pos[0] * self.squaresize + self.squaresize/2)
        pos_y = int(self.yboundary + pos[1] * self.squaresize + self.squaresize/2)
        markersize = int((self.squaresize*0.7)/2 )

        color = self.colors[playercolor]
        pygame.draw.circle(self.screen, color, (pos_x, pos_y), markersize)


    def place(self, gridpos, color):
        try:
            self.board.place(gridpos, color)
        except self.board.OccupiedException as e:
            return
        board_status = self.board.check_board()
        if board_status is not None:
            print("winning move ((x,y),color)={pos} in direction {dir}".format(pos=board_status[0], dir=board_status[1]))
            # game over


class Player:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.turn = None
        self.points = 0
        self.last_move = None

