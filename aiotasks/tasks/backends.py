"""Backend implementations and manager factory for aiotasks."""

import asyncio
import atexit
import contextlib
import logging
import os
from typing import Any

with contextlib.suppress(ImportError):
    import uvloop

    # Set uvloop as default event loop policy if available and not in debug mode
    if not os.getenv("AIOTASK_DEBUG"):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logging.getLogger("aiotasks").debug("uvloop enabled")

from ..core.exceptions import AioTasksValueError
from .bases import AsyncTaskBase
from .memory import AsyncTaskDelayMemory, AsyncTaskSubscribeMemory
from .redis import AsyncTaskDelayRedis, AsyncTaskSubscribeRedis

log = logging.getLogger("aiotasks")


class MemoryBackend(AsyncTaskDelayMemory, AsyncTaskSubscribeMemory, AsyncTaskBase):
    """In-memory backend for development and testing.

    This backend stores tasks in memory and is useful for development,
    testing, and single-process applications. Data is not persisted.

    Attributes:
        prefix: Prefix for task names and channels
    """

    def __init__(
        self,
        dsn: str,
        prefix: str = "aiotasks",
        **kwargs: Any,
    ) -> None:
        """Initialize the memory backend.

        Args:
            dsn: Connection string (ignored for memory backend)
            prefix: Prefix for all task names and channels
            **kwargs: Additional arguments (loop is deprecated)
        """
        kwargs.pop("loop", None)  # Remove deprecated loop parameter
        self.prefix = prefix

        AsyncTaskSubscribeMemory.__init__(self, prefix=prefix)
        AsyncTaskDelayMemory.__init__(self, prefix=prefix)
        AsyncTaskBase.__init__(self, dsn=dsn)


class RedisBackend(AsyncTaskSubscribeRedis, AsyncTaskDelayRedis, AsyncTaskBase):
    """Redis backend for distributed task processing.

    This backend uses Redis for task storage and pub/sub, enabling
    distributed task processing across multiple workers.

    Attributes:
        prefix: Prefix for all Redis keys and channels
    """

    def __init__(
        self,
        dsn: str,
        prefix: str = "aiotasks",
        **kwargs: Any,
    ) -> None:
        """Initialize the Redis backend.

        Args:
            dsn: Redis connection string (e.g., "redis://localhost:6379/0")
            prefix: Prefix for all Redis keys and channels
            **kwargs: Additional arguments (loop is deprecated)
        """
        kwargs.pop("loop", None)  # Remove deprecated loop parameter

        AsyncTaskSubscribeRedis.__init__(self, dsn=dsn, prefix=prefix)
        AsyncTaskDelayRedis.__init__(self, dsn=dsn, prefix=prefix)
        AsyncTaskBase.__init__(self, dsn=dsn)

        # Register cleanup on exit
        atexit.register(self.stop)


def build_manager(
    dsn: str = "memory://",
    prefix: str = "aiotasks",
    **kwargs: Any,
) -> AsyncTaskBase:
    """Build and configure a task manager backend.

    This is the main factory function for creating aiotasks managers.
    It selects the appropriate backend based on the DSN scheme.

    Args:
        dsn: Data Source Name specifying the backend
            - "memory://" for in-memory backend (development/testing)
            - "redis://host:port/db" for Redis backend (production)
            - "amqp://..." for RabbitMQ backend (future)
            - "zmq://..." for ZeroMQ backend (future)
        prefix: Prefix for all task names, keys, and channels
        **kwargs: Additional backend-specific arguments

    Returns:
        Configured task manager instance

    Raises:
        AioTasksValueError: If the DSN scheme is not recognized

    Examples:
        >>> # Create memory backend for testing
        >>> manager = build_manager("memory://")
        >>>
        >>> # Create Redis backend for production
        >>> manager = build_manager("redis://localhost:6379/0")
        >>>
        >>> # Create with custom prefix
        >>> manager = build_manager("redis://localhost:6379/0", prefix="myapp")
    """
    # Deprecated loop parameter handling
    kwargs.pop("loop", None)

    # Validate and normalize prefix
    if not prefix:
        log.warning("Empty prefix provided, using 'aiotasks'")
        prefix = "aiotasks"
    prefix = str(prefix)

    # Select backend based on DSN scheme
    if dsn.startswith("memory"):
        log.debug("Creating memory backend")
        manager = MemoryBackend(dsn=dsn, prefix=prefix)
    elif dsn.startswith("redis"):
        log.debug("Creating Redis backend with DSN: %s", dsn)
        manager = RedisBackend(dsn=dsn, prefix=prefix)
    else:
        msg = f"Unsupported DSN scheme: {dsn}. Use 'memory://' or 'redis://'"
        raise AioTasksValueError(msg)

    # Store manager globally for current_app() access
    import builtins

    builtins.__aiotasks__ = manager  # type: ignore[attr-defined]

    return manager


__all__ = ("build_manager", "MemoryBackend", "RedisBackend")
