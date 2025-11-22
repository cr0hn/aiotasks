"""Logging configuration for aiotasks."""

import logging
from pathlib import Path
from typing import Any

from colorlog import ColoredFormatter

CONSOLE_LEVEL = 1000


def console(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
    """Log a message with console level."""
    if self.isEnabledFor(CONSOLE_LEVEL):
        self._log(CONSOLE_LEVEL, message, args, **kwargs)


def setup_logging(name: str) -> None:
    """Setup initial logging configuration.

    Args:
        name: Name of the logger to configure
    """
    if not isinstance(name, str):
        msg = f"Logger name must be a string, got {type(name)}"
        raise TypeError(msg)

    # Add console level
    logging.addLevelName(CONSOLE_LEVEL, "CONSOLE_LEVEL")

    # Add custom console methods to Logger class
    logging.Logger.console = console  # type: ignore[attr-defined]
    logging.Logger.raw_console = console  # type: ignore[attr-defined]

    # Init logger
    logger = logging.getLogger(name)

    # Handler: console
    formatter = ColoredFormatter(
        "[ %(log_color)s*%(reset)s ] %(blue)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
            "CONSOLE_LEVEL": "green",
        },
        secondary_log_colors={},
        style="%",
    )

    log_console = logging.StreamHandler()
    log_console.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(log_console)


def setup_file_logger(location_file_name: str) -> None:
    """Setup file logging.

    Args:
        location_file_name: Name/location for the log file
    """
    logger = logging.getLogger(location_file_name)

    # Set file log format
    file_format = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S")

    log_path = Path.cwd() / "aiotasks.log"
    log_file = logging.FileHandler(filename=log_path)

    log_file.setFormatter(file_format)
    logger.addHandler(log_file)


__all__ = ("CONSOLE_LEVEL", "setup_file_logger", "setup_logging")
