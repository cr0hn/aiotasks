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

# Optional backends - import only if dependencies are available
try:
    from .amqp import AsyncTaskDelayAMQP, AsyncTaskSubscribeAMQP

    AMQP_AVAILABLE = True
except ImportError:
    AMQP_AVAILABLE = False

try:
    from .zmq import AsyncTaskDelayZMQ, AsyncTaskSubscribeZMQ

    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False

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
        concurrency: int = 5,
        max_retries: int = 3,
        task_ttl: int = 3600,
        **kwargs: Any,
    ) -> None:
        """Initialize the memory backend.

        Args:
            dsn: Connection string (ignored for memory backend)
            prefix: Prefix for all task names and channels
            concurrency: Maximum number of concurrent tasks
            max_retries: Maximum number of retry attempts for failed tasks
            task_ttl: Time-to-live for tasks in seconds
            **kwargs: Additional arguments (loop is deprecated)
        """
        kwargs.pop("loop", None)  # Remove deprecated loop parameter
        self.prefix = prefix

        AsyncTaskSubscribeMemory.__init__(self, prefix=prefix)
        AsyncTaskDelayMemory.__init__(
            self,
            prefix=prefix,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
        )
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
        concurrency: int = 5,
        max_retries: int = 3,
        task_ttl: int = 3600,
        **kwargs: Any,
    ) -> None:
        """Initialize the Redis backend.

        Args:
            dsn: Redis connection string (e.g., "redis://localhost:6379/0")
            prefix: Prefix for all Redis keys and channels
            concurrency: Maximum number of concurrent tasks
            max_retries: Maximum number of retry attempts for failed tasks
            task_ttl: Time-to-live for tasks in seconds
            **kwargs: Additional arguments (loop is deprecated)
        """
        kwargs.pop("loop", None)  # Remove deprecated loop parameter

        AsyncTaskSubscribeRedis.__init__(self, dsn=dsn, prefix=prefix)
        AsyncTaskDelayRedis.__init__(
            self,
            dsn=dsn,
            prefix=prefix,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
        )
        AsyncTaskBase.__init__(self, dsn=dsn)

        # Register cleanup on exit
        atexit.register(self.stop)


if AMQP_AVAILABLE:

    class AMQPBackend(AsyncTaskSubscribeAMQP, AsyncTaskDelayAMQP, AsyncTaskBase):  # type: ignore[misc]
        """AMQP/RabbitMQ backend for distributed task processing.

        This backend uses RabbitMQ (or any AMQP broker) for task storage and pub/sub,
        enabling highly reliable distributed task processing.

        Attributes:
            prefix: Prefix for all exchanges and queues
        """

        def __init__(
            self,
            dsn: str,
            prefix: str = "aiotasks",
            concurrency: int = 5,
            max_retries: int = 3,
            task_ttl: int = 3600,
            **kwargs: Any,
        ) -> None:
            """Initialize the AMQP backend.

            Args:
                dsn: AMQP connection string (e.g., "amqp://guest:guest@localhost:5672/")
                prefix: Prefix for all exchanges and queues
                concurrency: Maximum number of concurrent tasks
                max_retries: Maximum number of retry attempts for failed tasks
                task_ttl: Time-to-live for tasks in seconds
                **kwargs: Additional arguments (loop is deprecated)
            """
            if not AMQP_AVAILABLE:
                msg = "AMQP backend requires 'aio-pika'. Install with: pip install aiotasks[amqp]"
                raise ImportError(msg)

            kwargs.pop("loop", None)

            AsyncTaskSubscribeAMQP.__init__(self, dsn=dsn, prefix=prefix)
            AsyncTaskDelayAMQP.__init__(
                self,
                dsn=dsn,
                prefix=prefix,
                concurrency=concurrency,
                max_retries=max_retries,
                task_ttl=task_ttl,
            )
            AsyncTaskBase.__init__(self, dsn=dsn)

            atexit.register(self.stop)


if ZMQ_AVAILABLE:

    class ZMQBackend(AsyncTaskSubscribeZMQ, AsyncTaskDelayZMQ, AsyncTaskBase):  # type: ignore[misc]
        """ZeroMQ backend for high-performance task processing.

        This backend uses ZeroMQ for task distribution, providing extremely
        high throughput and low latency.

        Attributes:
            prefix: Prefix for all topics and queues
        """

        def __init__(
            self,
            dsn: str,
            prefix: str = "aiotasks",
            concurrency: int = 5,
            max_retries: int = 3,
            task_ttl: int = 3600,
            **kwargs: Any,
        ) -> None:
            """Initialize the ZeroMQ backend.

            Args:
                dsn: ZeroMQ connection string (e.g., "zmq://localhost:5555")
                prefix: Prefix for all topics and queues
                concurrency: Maximum number of concurrent tasks
                max_retries: Maximum number of retry attempts for failed tasks
                task_ttl: Time-to-live for tasks in seconds
                **kwargs: Additional arguments (loop is deprecated)
            """
            if not ZMQ_AVAILABLE:
                msg = "ZMQ backend requires 'pyzmq'. Install with: pip install aiotasks[zeromq]"
                raise ImportError(msg)

            kwargs.pop("loop", None)

            AsyncTaskSubscribeZMQ.__init__(self, dsn=dsn, prefix=prefix)
            AsyncTaskDelayZMQ.__init__(
                self,
                dsn=dsn,
                prefix=prefix,
                concurrency=concurrency,
                max_retries=max_retries,
                task_ttl=task_ttl,
            )
            AsyncTaskBase.__init__(self, dsn=dsn)

            atexit.register(self.stop)


def build_manager(
    dsn: str = "memory://",
    prefix: str = "aiotasks",
    concurrency: int = 5,
    max_retries: int = 3,
    task_ttl: int = 3600,
    **kwargs: Any,
) -> AsyncTaskBase:
    """Build and configure a task manager backend.

    This is the main factory function for creating aiotasks managers.
    It selects the appropriate backend based on the DSN scheme.

    Args:
        dsn: Data Source Name specifying the backend
            - "memory://" for in-memory backend (development/testing)
            - "redis://host:port/db" for Redis backend (production)
            - "amqp://user:pass@host:port/" for RabbitMQ backend
            - "zmq://host:port" for ZeroMQ backend
        prefix: Prefix for all task names, keys, and channels
        concurrency: Maximum number of concurrent tasks (default: 5)
        max_retries: Maximum number of retry attempts for failed tasks (default: 3)
        task_ttl: Time-to-live for tasks in seconds (default: 3600)
        **kwargs: Additional backend-specific arguments

    Returns:
        Configured task manager instance

    Raises:
        AioTasksValueError: If the DSN scheme is not recognized
        ImportError: If required dependencies for backend are not installed

    Examples:
        >>> # Create memory backend for testing
        >>> manager = build_manager("memory://")
        >>>
        >>> # Create Redis backend for production
        >>> manager = build_manager("redis://localhost:6379/0")
        >>>
        >>> # Create AMQP backend with RabbitMQ
        >>> manager = build_manager("amqp://guest:guest@localhost:5672/")
        >>>
        >>> # Create ZeroMQ backend for high performance
        >>> manager = build_manager("zmq://localhost:5555")
        >>>
        >>> # Create with custom prefix and retry settings
        >>> manager = build_manager(
        ...     "redis://localhost:6379/0",
        ...     prefix="myapp",
        ...     max_retries=5,
        ...     task_ttl=7200
        ... )
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
        manager = MemoryBackend(
            dsn=dsn,
            prefix=prefix,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
        )
    elif dsn.startswith("redis"):
        log.debug("Creating Redis backend with DSN: %s", dsn)
        manager = RedisBackend(
            dsn=dsn,
            prefix=prefix,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
        )
    elif dsn.startswith("amqp"):
        log.debug("Creating AMQP backend with DSN: %s", dsn)
        manager = AMQPBackend(
            dsn=dsn,
            prefix=prefix,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
        )
    elif dsn.startswith("zmq"):
        log.debug("Creating ZMQ backend with DSN: %s", dsn)
        manager = ZMQBackend(
            dsn=dsn,
            prefix=prefix,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
        )
    else:
        msg = (
            f"Unsupported DSN scheme: {dsn}. "
            "Supported: 'memory://', 'redis://', 'amqp://', 'zmq://'"
        )
        raise AioTasksValueError(msg)

    # Store manager globally for current_app() access
    import builtins

    builtins.__aiotasks__ = manager  # type: ignore[attr-defined]

    return manager


# Build __all__ dynamically based on available backends
__all__ = ["MemoryBackend", "RedisBackend", "build_manager"]
if AMQP_AVAILABLE:
    __all__.append("AMQPBackend")
if ZMQ_AVAILABLE:
    __all__.append("ZMQBackend")
__all__ = tuple(__all__)
