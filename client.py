#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game client
"""

from fiveinarow import FiveInaRow
from communicator import TimeoutException

fir = None
is_connected = False
while not is_connected:
    try:
        fir = FiveInaRow(FiveInaRow.CLIENT)
        is_connected = True
    except TimeoutException as e:
        print("Can not connect, connection timed out")

if fir is not None:
    fir.set_player('Levi')
    fir.start_game()
