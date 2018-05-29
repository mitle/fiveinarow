#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game server
"""

from fiveinarow import FiveInaRow

fir = FiveInaRow(FiveInaRow.SERVER)
fir.set_player('Kata')
fir.start_game()