#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game server
"""

import logging
from fiveinarow.fiveinarow import FiveInaRow

logging.info("Starting server instance")
fir = FiveInaRow(FiveInaRow.SERVER)
fir.start()
fir.start_game()