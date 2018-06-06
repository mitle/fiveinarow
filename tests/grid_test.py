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
import  random

from fiveinarow.game_board import Grid, Board, Player

with open('../config.txt', 'r') as c:
    conf = json.load(c)

random.seed(6453)

"""
tests = [((640, 640), (10, 10)),
         ((640, 640), (15, 10)),
         ((640, 640), (10, 15)),
         ((640, 480), (10, 10)),
         ((480, 640), (10, 10)),
         ((640, 480), (4, 5)),
         ((640, 480), (20, 4)),
         ((640, 480), (4, 20)),
         ((640, 480), (20, 15)),
         ((480, 640), (15, 20)),
         ((640, 480), (20, 2)),
         ]
"""
tests = []

for _ in range(10):
    w, h = random.randint(100, 800), random.randint(100, 800)
    x, y = random.randint(4, 20), random.randint(4, 20)
    tests.append(((w, h), (x, y)))



pygame.init()

for ss, gs in tests:
    screen_size = ss
    conf['numgridx'], conf['numgridy'] = gs
    print(ss, gs, ss[0]/ss[1], gs[0]/gs[1])

    clock = pygame.time.Clock()
    screen = pygame.display.set_mode(screen_size)

    grid = Grid(screen=screen, clock=clock, conf=conf)

    done = False
    while not done:
        screen.fill(conf['bgcolor'])
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_F4 and event.mod == pygame.KMOD_LALT):
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                done = True

        grid.draw_grid(animate=False)

        pygame.display.update()
        clock.tick(25)
