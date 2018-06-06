#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test for grid draw function
"""

import logging
import pygame
import json
import sys
import time
import os

from fiveinarow.game_board import Grid, Board, Player

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((640,640))

with open('../config.txt', 'r') as c:
    conf = json.load(c)

grid = Grid(screen=screen, clock=clock, conf=conf)

while True:
    screen.fill(conf['bgcolor'])
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_F4 and event.mod == pygame.KMOD_LALT):
            pygame.quit()
            sys.exit(0)

    grid.draw_grid(animate=False)

    pygame.display.update()
    clock.tick(25)
