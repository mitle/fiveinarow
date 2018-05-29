#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game client
"""

import logging
from fiveinarow import FiveInaRow
from communicator import TimeoutException


logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s', level=logging.DEBUG)

while True:
    try:
        fir = FiveInaRow(FiveInaRow.CLIENT)
        break
    except TimeoutException:
        pass

fir.set_player('Levi')
fir.start_game()