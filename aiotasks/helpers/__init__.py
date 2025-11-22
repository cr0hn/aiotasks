"""Helper utilities for aiotasks."""

from dataclasses import dataclass
from urllib.parse import urlparse

BANNER = """
    ___    ____  _______           __
   /   |  /  _/ / ____(_)___  ____/ /_
  / /| |  / /  / /   / / __ \\/ __  / / / /
 / ___ |_/ /  / /___/ / / / / /_/ /  \\_\\
/_/  |_/___/  \\____/_/_/ /_/\\__,_/
  Async Task Queue for Python 3.12+
"""


@dataclass(frozen=True)
class DSNConfig:
    """Configuration parsed from a DSN string."""

    user: str | None
    password: str | None
    host: str
    port: int
    db: str | int


def parse_dsn(
    dsn: str,
    default_port: int | None = None,
    default_db: int | str | None = None,
) -> DSNConfig:
    """Parse a DSN string and return configuration.

    Args:
        dsn: Connection string (e.g., "redis://user:pass@localhost:6379/0")
        default_port: Default port if not specified in DSN
        default_db: Default database if not specified in DSN

    Returns:
        DSNConfig object with parsed connection details

    Examples:
        >>> config = parse_dsn("redis://:password@127.0.0.1:6379/0")
        >>> config.host
        '127.0.0.1'
        >>> config.port
        6379
        >>> config.db
        '0'
    """
    parsed = urlparse(dsn)

    # Extract credentials
    user: str | None = None
    password: str | None = None

    if parsed.username:
        user = parsed.username
    if parsed.password:
        password = parsed.password

    # Extract host and port
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port or 6379

    # Extract database
    db: str | int = ""
    if parsed.path and len(parsed.path) > 1:
        db = parsed.path.lstrip("/")
        # Try to convert to int if it's a number
        if db.isdigit():
            db = int(db)
    elif default_db is not None:
        db = default_db

    return DSNConfig(
        user=user,
        password=password,
        host=host,
        port=port,
        db=db,
    )


__all__ = ("BANNER", "DSNConfig", "parse_dsn")
