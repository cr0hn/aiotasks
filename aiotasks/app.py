"""Celery-like application interface for AioTasks.

Modern Python 3.12+ API that mimics Celery's familiar interface.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .tasks.backends import build_manager

if TYPE_CHECKING:
    from collections.abc import Callable

    from .tasks.bases import AsyncTaskBase

log = logging.getLogger("aiotasks")


class AioTasks:
    """Celery-like application for distributed async task processing.

    Usage (Celery-style):
        >>> app = AioTasks('myapp')
        >>>
        >>> @app.task
        >>> async def add(x: int, y: int) -> int:
        ...     return x + y
        >>>
        >>> # Queue the task
        >>> await add.delay(4, 5)

    Args:
        name: Application name (like Celery's app name)
        broker: Broker DSN (redis://, amqp://, zmq://, memory://)
        backend: Result backend DSN (optional, for future result storage)
        pool: Execution pool type (async, thread, or process)
        **config: Additional configuration options

    Examples:
        >>> # Memory backend (development)
        >>> app = AioTasks('myapp', broker='memory://')
        >>>
        >>> # Redis backend (production)
        >>> app = AioTasks('myapp', broker='redis://localhost:6379/0')
        >>>
        >>> # RabbitMQ backend (enterprise)
        >>> app = AioTasks('myapp', broker='amqp://guest:guest@localhost/')
        >>>
        >>> # ZeroMQ backend (high performance)
        >>> app = AioTasks('myapp', broker='zmq://localhost:5555')
        >>>
        >>> # Thread pool for blocking I/O tasks
        >>> app = AioTasks('myapp', broker='redis://localhost:6379/0', pool='thread')
        >>>
        >>> # Process pool for CPU-intensive tasks
        >>> app = AioTasks('myapp', broker='redis://localhost:6379/0', pool='process', concurrency=4)
        >>>
        >>> # Celery compatibility - interoperate with Celery workers
        >>> app = AioTasks('myapp', broker='redis://localhost:6379/0', celery_compat=True)
    """

    def __init__(
        self,
        name: str = "aiotasks",
        *,
        broker: str = "memory://",
        backend: str | None = None,
        concurrency: int = 5,
        max_retries: int = 3,
        task_ttl: int = 3600,
        pool: str = "async",
        celery_compat: bool = False,
        **config: Any,
    ) -> None:
        """Initialize AioTasks application.

        Args:
            name: Application name
            broker: Message broker DSN
            backend: Result backend DSN (optional)
            concurrency: Max concurrent tasks
            max_retries: Max retry attempts per task
            task_ttl: Task time-to-live in seconds
            pool: Execution pool type (async, thread, or process)
            celery_compat: Enable Celery Protocol v2 compatibility for interoperability
            **config: Additional config options
        """
        self.name = name
        self.broker_url = broker
        self.backend_url = backend
        self.pool = pool
        self.celery_compat = celery_compat
        self.conf = config

        # Create underlying manager
        self._manager: AsyncTaskBase = build_manager(
            dsn=broker,
            prefix=name,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
            pool=pool,
            celery_compat=celery_compat,
        )

        compat_msg = " (Celery-compatible)" if celery_compat else ""
        log.info(f"AioTasks app '{name}' initialized with broker: {broker}, pool: {pool}{compat_msg}")

    def task(self, name: str | None = None, **options: Any) -> Callable:
        """Decorator to register async functions as tasks (Celery-style).

        Args:
            name: Custom task name (optional)
            **options: Task options (for future use)

        Returns:
            Decorated function with .delay() method

        Example:
            >>> @app.task
            >>> async def send_email(to: str, subject: str):
            ...     await asyncio.sleep(1)
            ...     print(f"Email sent to {to}")
            >>>
            >>> # Queue the task
            >>> await send_email.delay("user@example.com", "Hello")
        """
        return self._manager.task(name=name)

    def run(self) -> None:
        """Start the task worker (Celery-style).

        Starts processing tasks from the queue.
        """
        log.info(f"Starting worker for app '{self.name}'...")
        self._manager.run()

    def stop(self) -> None:
        """Stop the task worker (Celery-style).

        Stops processing tasks and cleans up resources.
        """
        log.info(f"Stopping worker for app '{self.name}'...")
        self._manager.stop()

    async def wait(
        self,
        *,
        timeout: float = 0,
        exit_on_finish: bool = False,
        wait_timeout: float = 1.0,
    ) -> None:
        """Wait for tasks to complete.

        Args:
            timeout: Max time to wait (0 = infinite)
            exit_on_finish: Exit when all tasks complete
            wait_timeout: Polling interval
        """
        await self._manager.wait(
            timeout=timeout,
            exit_on_finish=exit_on_finish,
            wait_timeout=wait_timeout,
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"<AioTasks app='{self.name}' broker='{self.broker_url}'>"


__all__ = ("AioTasks",)
