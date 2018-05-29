#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game server
"""

import logging
from fiveinarow import FiveInaRow

logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s', level=logging.DEBUG)

fir = FiveInaRow(FiveInaRow.SERVER)
fir.set_player('Kata')
fir.start_game()