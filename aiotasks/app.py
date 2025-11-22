"""Celery-like application interface for AioTasks.

Modern Python 3.12+ API that mimics Celery's familiar interface.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .dlq import DeadLetterQueue, FailedTask
from .periodic import PeriodicScheduler, Schedule
from .result_backend import TaskResult, build_result_backend
from .tasks.backends import build_manager

if TYPE_CHECKING:
    from collections.abc import Callable

    from .periodic import PeriodicTask
    from .result_backend import ResultBackend
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

        # Create result backend if configured
        self._result_backend: ResultBackend | None = build_result_backend(
            backend=backend,
            ttl=task_ttl,
        )

        # Store result backend in manager for task result storage
        if self._result_backend:
            self._manager._result_backend = self._result_backend

        # Create periodic scheduler (Celery Beat style)
        self._scheduler: PeriodicScheduler = PeriodicScheduler(self)

        # Create dead letter queue for failed tasks
        self._dlq: DeadLetterQueue = DeadLetterQueue(prefix=name)

        # Store DLQ in manager for task failure handling
        self._manager._dlq = self._dlq

        # Prometheus metrics (optional, initialized on demand)
        self._metrics: Any = None

        # Rate limiter (optional, initialized on demand)
        self._rate_limiter: Any = None

        # Dashboard server (optional, initialized on demand)
        self._dashboard: Any = None

        compat_msg = " (Celery-compatible)" if celery_compat else ""
        backend_msg = f", backend: {backend}" if backend else ""
        log.info(
            f"AioTasks app '{name}' initialized with broker: {broker}, pool: {pool}{compat_msg}{backend_msg}"
        )

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

    # Result Backend Methods

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Get task result by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task result or None if not found or no backend configured

        Example:
            >>> task = add.delay(4, 5)
            >>> result = await app.get_result(task.task_id)
            >>> print(result.status, result.result)
            success 9
        """
        if self._result_backend is None:
            log.warning("No result backend configured, cannot retrieve results")
            return None

        return await self._result_backend.get_result(task_id)

    async def wait_for_result(
        self,
        task_id: str,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> TaskResult:
        """Wait for task result with polling.

        Args:
            task_id: Task identifier
            timeout: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds

        Returns:
            Task result when available

        Raises:
            RuntimeError: If no result backend configured
            TimeoutError: If timeout is reached
            RuntimeError: If task failed

        Example:
            >>> task = long_task.delay(data)
            >>> result = await app.wait_for_result(task.task_id, timeout=60)
            >>> print(result.result)
        """
        if self._result_backend is None:
            msg = "No result backend configured, cannot wait for results"
            raise RuntimeError(msg)

        return await self._result_backend.wait_for_result(
            task_id=task_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )

    async def delete_result(self, task_id: str) -> bool:
        """Delete task result.

        Args:
            task_id: Task identifier

        Returns:
            True if deleted, False if not found or no backend

        Example:
            >>> deleted = await app.delete_result(task_id)
        """
        if self._result_backend is None:
            return False

        return await self._result_backend.delete_result(task_id)

    # Periodic Scheduler Methods

    def add_periodic_task(
        self,
        name: str,
        schedule: Schedule,
        task: str | Callable,
        args: tuple = (),
        kwargs: dict | None = None,
        enabled: bool = True,
    ) -> PeriodicTask:
        """Add periodic task to scheduler.

        Args:
            name: Task name (unique identifier)
            schedule: Schedule object (use every() or crontab())
            task: Task function name or callable
            args: Positional arguments for task
            kwargs: Keyword arguments for task
            enabled: Whether task is enabled

        Returns:
            Created PeriodicTask instance

        Example:
            >>> from aiotasks import every, crontab
            >>>
            >>> # Run every hour
            >>> app.add_periodic_task(
            ...     name="hourly_cleanup",
            ...     schedule=every(hours=1),
            ...     task="cleanup",
            ... )
            >>>
            >>> # Run daily at 7:30 AM
            >>> app.add_periodic_task(
            ...     name="daily_report",
            ...     schedule=crontab(hour="7", minute="30"),
            ...     task="generate_report",
            ... )
        """
        return self._scheduler.add_task(
            name=name,
            schedule=schedule,
            task=task,
            args=args,
            kwargs=kwargs,
            enabled=enabled,
        )

    def remove_periodic_task(self, name: str) -> bool:
        """Remove periodic task.

        Args:
            name: Task name

        Returns:
            True if removed, False if not found
        """
        return self._scheduler.remove_task(name)

    def get_periodic_task(self, name: str) -> PeriodicTask | None:
        """Get periodic task by name."""
        return self._scheduler.get_task(name)

    def list_periodic_tasks(self) -> list[PeriodicTask]:
        """List all periodic tasks."""
        return self._scheduler.list_tasks()

    async def start_scheduler(self) -> None:
        """Start periodic task scheduler (Celery Beat style).

        Example:
            >>> # Start scheduler in background
            >>> await app.start_scheduler()
        """
        await self._scheduler.start()

    async def stop_scheduler(self) -> None:
        """Stop periodic task scheduler."""
        await self._scheduler.stop()

    # Dead Letter Queue Methods

    async def get_failed_task(self, task_id: str) -> FailedTask | None:
        """Get failed task from DLQ.

        Args:
            task_id: Task identifier

        Returns:
            Failed task or None if not found

        Example:
            >>> failed = await app.get_failed_task("task123")
            >>> if failed:
            ...     print(f"Error: {failed.error}")
        """
        return await self._dlq.get_task(task_id)

    async def list_failed_tasks(
        self,
        limit: int | None = None,
        task_name: str | None = None,
    ) -> list[FailedTask]:
        """List failed tasks in DLQ.

        Args:
            limit: Maximum number of tasks to return
            task_name: Filter by task name (optional)

        Returns:
            List of failed tasks

        Example:
            >>> # List all failed tasks
            >>> failed = await app.list_failed_tasks(limit=10)
            >>>
            >>> # List failed email tasks
            >>> failed_emails = await app.list_failed_tasks(task_name="send_email")
        """
        return await self._dlq.list_tasks(limit=limit, task_name=task_name)

    async def retry_failed_task(self, task_id: str) -> bool:
        """Retry a failed task from DLQ.

        Args:
            task_id: Task identifier

        Returns:
            True if task was queued for retry, False if not found

        Example:
            >>> # Retry specific failed task
            >>> success = await app.retry_failed_task("task123")
        """
        return await self._dlq.retry_task(task_id, self)

    async def retry_failed_tasks(
        self,
        task_name: str | None = None,
        limit: int | None = None,
    ) -> int:
        """Retry multiple failed tasks from DLQ.

        Args:
            task_name: Retry only tasks with this name (optional)
            limit: Maximum number of tasks to retry (optional)

        Returns:
            Number of tasks successfully queued for retry

        Example:
            >>> # Retry all failed email tasks
            >>> count = await app.retry_failed_tasks(task_name="send_email")
            >>> print(f"Retried {count} tasks")
        """
        return await self._dlq.retry_all(self, task_name=task_name, limit=limit)

    async def clear_failed_tasks(self, task_name: str | None = None) -> int:
        """Clear failed tasks from DLQ.

        Args:
            task_name: Clear only tasks with this name (optional)

        Returns:
            Number of tasks removed

        Example:
            >>> # Clear all failed tasks
            >>> count = await app.clear_failed_tasks()
            >>>
            >>> # Clear only failed email tasks
            >>> count = await app.clear_failed_tasks(task_name="send_email")
        """
        return await self._dlq.clear(task_name=task_name)

    def get_dlq_stats(self) -> dict[str, Any]:
        """Get DLQ statistics.

        Returns:
            Dictionary with DLQ stats

        Example:
            >>> stats = app.get_dlq_stats()
            >>> print(f"Total failed: {stats['total_tasks']}")
            >>> print(f"By task: {stats['by_task_name']}")
        """
        return self._dlq.get_stats()

    # Monitoring and Metrics Methods

    def setup_metrics(
        self,
        namespace: str | None = None,
        enable_http_server: bool = False,
        http_port: int = 9090,
    ) -> Any:
        """Setup Prometheus metrics for monitoring.

        Args:
            namespace: Metric namespace (default: app name)
            enable_http_server: Auto-start HTTP metrics server
            http_port: HTTP server port for /metrics endpoint

        Returns:
            PrometheusMetrics instance

        Example:
            >>> app = AioTasks('myapp', broker='redis://localhost')
            >>> metrics = app.setup_metrics(enable_http_server=True, http_port=9090)
            >>>
            >>> # Metrics available at http://localhost:9090/metrics
        """
        from .monitoring import setup_metrics

        if self._metrics is not None:
            log.warning("Metrics already initialized")
            return self._metrics

        namespace = namespace or self.name
        self._metrics = setup_metrics(
            app=self,
            namespace=namespace,
            enable_http_server=enable_http_server,
            http_port=http_port,
        )

        # Store metrics in manager for automatic tracking
        if hasattr(self._manager, "_metrics"):
            self._manager._metrics = self._metrics

        return self._metrics

    def get_metrics(self) -> Any:
        """Get metrics instance.

        Returns:
            PrometheusMetrics instance or None if not initialized
        """
        return self._metrics

    # Dashboard Methods

    def setup_dashboard(
        self,
        host: str = "127.0.0.1",
        port: int = 5555,
        enable_cors: bool = True,
    ) -> Any:
        """Setup web dashboard for monitoring and management.

        Args:
            host: Server host address
            port: Server port
            enable_cors: Enable CORS for API access

        Returns:
            DashboardServer instance

        Example:
            >>> app = AioTasks('myapp', broker='redis://localhost')
            >>> dashboard = app.setup_dashboard(host='0.0.0.0', port=5555)
            >>> await dashboard.start()
            >>>
            >>> # Dashboard available at http://localhost:5555
        """
        from .dashboard import DashboardServer

        if self._dashboard is not None:
            log.warning("Dashboard already initialized")
            return self._dashboard

        self._dashboard = DashboardServer(
            app=self,
            host=host,
            port=port,
            enable_cors=enable_cors,
        )

        return self._dashboard

    async def start_dashboard(
        self,
        host: str = "127.0.0.1",
        port: int = 5555,
        enable_cors: bool = True,
    ) -> None:
        """Setup and start dashboard server.

        Args:
            host: Server host address
            port: Server port
            enable_cors: Enable CORS for API access

        Example:
            >>> app = AioTasks('myapp', broker='redis://localhost')
            >>> await app.start_dashboard(port=5555)
        """
        dashboard = self.setup_dashboard(host=host, port=port, enable_cors=enable_cors)
        await dashboard.start()

    def get_dashboard(self) -> Any:
        """Get dashboard instance.

        Returns:
            DashboardServer instance or None if not initialized
        """
        return self._dashboard

    def __repr__(self) -> str:
        """String representation."""
        return f"<AioTasks app='{self.name}' broker='{self.broker_url}'>"


__all__ = ("AioTasks",)
