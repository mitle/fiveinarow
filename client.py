#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game client
"""

import logging
from fiveinarow.fiveinarow import FiveInaRow
from fiveinarow.communicator import TimeoutException



logging.info("Starting server instance")
while True:
    try:
        fir = FiveInaRow(FiveInaRow.CLIENT)
        fir.start()
        break
    except TimeoutException:
        pass

fir.start_game()
