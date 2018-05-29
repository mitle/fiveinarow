#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game client
"""

from fiveinarow import FiveInaRow
from communicator import TimeoutException


while True:
    try:
        fir = FiveInaRow(FiveInaRow.CLIENT)
        break
    except TimeoutException:
        pass

fir.set_player('Levi')
fir.start_game()