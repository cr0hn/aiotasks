# -*- coding: utf-8 -*-

import os
import logging
import logging.handlers

from colorlog import ColoredFormatter

CONSOLE_LEVEL = 1000


def setup_logging(name):
    """
    Setup initial logging configuration
    """

    assert isinstance(name, str)
    
    # Add console level
    logging.addLevelName(CONSOLE_LEVEL, "CONSOLE_LEVEL")

    def console(self, message, *args, **kws):  # pragma no cover
        # Yes, logger takes its '*args' as 'args'.
        if self.isEnabledFor(CONSOLE_LEVEL):
            self._log(CONSOLE_LEVEL, message, args, **kws)

    logging.Logger.console = console

    # Init logger
    logger = logging.getLogger(name)

    # Set file log format
    file_format = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    log_file = logging.FileHandler(filename=os.path.join(os.getcwd(), "aiotasks.log"))

    log_file.setFormatter(file_format)

    # Handler: console
    formatter = ColoredFormatter(
        "[ %(log_color)s*%(reset)s ] %(blue)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'white',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
            'CONSOLE_LEVEL': 'green'
        },
        secondary_log_colors={},
        style='%'
    )
    log_console = logging.StreamHandler()
    log_console.setFormatter(formatter)

    # --------------------------------------------------------------------------
    # Add all of handlers to logger config
    # --------------------------------------------------------------------------
    logger.addHandler(log_console)
    logger.addHandler(log_file)

__all__ = ("setup_logging", "CONSOLE_LEVEL")
