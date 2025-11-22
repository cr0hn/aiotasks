"""Prometheus metrics and monitoring for AioTasks.

Provides automatic collection of task execution metrics compatible with
Prometheus monitoring system.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

log = logging.getLogger("aiotasks.monitoring")

# Try to import prometheus_client
try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        start_http_server,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    log.warning(
        "prometheus_client not installed. Metrics will not be collected. "
        "Install with: pip install aiotasks[monitoring]"
    )


class PrometheusMetrics:
    """Prometheus metrics collector for AioTasks.

    Automatically tracks:
    - Total tasks processed
    - Failed tasks
    - Task execution duration
    - Active workers
    - Queue length
    - Tasks in progress

    Usage:
        >>> from aiotasks import AioTasks
        >>> from aiotasks.monitoring import PrometheusMetrics
        >>>
        >>> app = AioTasks('myapp', broker='redis://localhost:6379/0')
        >>> metrics = PrometheusMetrics(app, namespace='myapp')
        >>> metrics.start_http_server(port=9090)
        >>>
        >>> # Metrics available at http://localhost:9090/metrics
    """

    def __init__(
        self,
        app: Any = None,
        namespace: str = "aiotasks",
        enable_http_server: bool = False,
        http_port: int = 9090,
    ) -> None:
        """Initialize Prometheus metrics collector.

        Args:
            app: AioTasks application instance (optional)
            namespace: Metric namespace prefix
            enable_http_server: Auto-start HTTP metrics server
            http_port: HTTP server port for metrics endpoint
        """
        if not PROMETHEUS_AVAILABLE:
            log.error("Prometheus metrics not available - prometheus_client not installed")
            self.enabled = False
            return

        self.enabled = True
        self.namespace = namespace
        self.app = app

        # Initialize metrics
        self._init_metrics()

        # Start HTTP server if requested
        if enable_http_server:
            self.start_http_server(http_port)

        log.info(f"Prometheus metrics initialized with namespace '{namespace}'")

    def _init_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        # Counter: Total tasks processed
        self.tasks_total = Counter(
            f"{self.namespace}_tasks_total",
            "Total number of tasks processed",
            ["task_name", "status"],  # status: success, failed, retry
        )

        # Counter: Failed tasks
        self.tasks_failed_total = Counter(
            f"{self.namespace}_tasks_failed_total",
            "Total number of failed tasks",
            ["task_name", "error_type"],
        )

        # Histogram: Task execution duration
        self.task_duration_seconds = Histogram(
            f"{self.namespace}_task_duration_seconds",
            "Task execution duration in seconds",
            ["task_name"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        )

        # Gauge: Active workers
        self.workers_active = Gauge(
            f"{self.namespace}_workers_active",
            "Number of active workers",
        )

        # Gauge: Tasks in progress
        self.tasks_in_progress = Gauge(
            f"{self.namespace}_tasks_in_progress",
            "Number of tasks currently being processed",
            ["task_name"],
        )

        # Gauge: Queue length
        self.queue_length = Gauge(
            f"{self.namespace}_queue_length",
            "Number of tasks waiting in queue",
            ["queue_name"],
        )

        # Counter: Tasks retried
        self.tasks_retried_total = Counter(
            f"{self.namespace}_tasks_retried_total",
            "Total number of task retries",
            ["task_name"],
        )

        # Gauge: DLQ size
        self.dlq_size = Gauge(
            f"{self.namespace}_dlq_size",
            "Number of tasks in dead letter queue",
        )

        # Counter: Periodic tasks executed
        self.periodic_tasks_total = Counter(
            f"{self.namespace}_periodic_tasks_total",
            "Total number of periodic tasks executed",
            ["task_name"],
        )

    def start_http_server(self, port: int = 9090) -> None:
        """Start HTTP server to expose metrics.

        Args:
            port: HTTP server port (default: 9090)
        """
        if not self.enabled:
            log.warning("Cannot start metrics server - Prometheus not available")
            return

        try:
            start_http_server(port)
            log.info(f"Prometheus metrics server started on port {port}")
            log.info(f"Metrics available at http://localhost:{port}/metrics")
        except OSError as e:
            log.error(f"Failed to start metrics server on port {port}: {e}")

    def get_latest_metrics(self) -> bytes:
        """Get latest metrics in Prometheus text format.

        Returns:
            Metrics in Prometheus exposition format
        """
        if not self.enabled:
            return b""

        return generate_latest()

    def record_task_start(self, task_name: str) -> None:
        """Record task start.

        Args:
            task_name: Name of the task
        """
        if not self.enabled:
            return

        self.tasks_in_progress.labels(task_name=task_name).inc()

    def record_task_complete(
        self,
        task_name: str,
        duration: float,
        status: str = "success",
    ) -> None:
        """Record task completion.

        Args:
            task_name: Name of the task
            duration: Task execution duration in seconds
            status: Task status (success, failed, retry)
        """
        if not self.enabled:
            return

        self.tasks_total.labels(task_name=task_name, status=status).inc()
        self.task_duration_seconds.labels(task_name=task_name).observe(duration)
        self.tasks_in_progress.labels(task_name=task_name).dec()

    def record_task_failure(
        self,
        task_name: str,
        error_type: str,
        duration: float,
    ) -> None:
        """Record task failure.

        Args:
            task_name: Name of the task
            error_type: Type of error that occurred
            duration: Task execution duration before failure
        """
        if not self.enabled:
            return

        self.tasks_failed_total.labels(task_name=task_name, error_type=error_type).inc()
        self.tasks_total.labels(task_name=task_name, status="failed").inc()
        self.task_duration_seconds.labels(task_name=task_name).observe(duration)
        self.tasks_in_progress.labels(task_name=task_name).dec()

    def record_task_retry(self, task_name: str) -> None:
        """Record task retry.

        Args:
            task_name: Name of the task
        """
        if not self.enabled:
            return

        self.tasks_retried_total.labels(task_name=task_name).inc()
        self.tasks_total.labels(task_name=task_name, status="retry").inc()

    def update_queue_length(self, queue_name: str, length: int) -> None:
        """Update queue length metric.

        Args:
            queue_name: Name of the queue
            length: Current queue length
        """
        if not self.enabled:
            return

        self.queue_length.labels(queue_name=queue_name).set(length)

    def update_workers_active(self, count: int) -> None:
        """Update active workers count.

        Args:
            count: Number of active workers
        """
        if not self.enabled:
            return

        self.workers_active.set(count)

    def update_dlq_size(self, size: int) -> None:
        """Update DLQ size metric.

        Args:
            size: Current DLQ size
        """
        if not self.enabled:
            return

        self.dlq_size.set(size)

    def record_periodic_task_execution(self, task_name: str) -> None:
        """Record periodic task execution.

        Args:
            task_name: Name of the periodic task
        """
        if not self.enabled:
            return

        self.periodic_tasks_total.labels(task_name=task_name).inc()

    @asynccontextmanager
    async def track_task_execution(
        self, task_name: str
    ) -> AsyncGenerator[None, None]:
        """Context manager to track task execution.

        Automatically records start, completion, and duration.

        Args:
            task_name: Name of the task

        Usage:
            >>> async with metrics.track_task_execution('my_task'):
            ...     await do_work()
        """
        if not self.enabled:
            yield
            return

        start_time = time.time()
        self.record_task_start(task_name)

        try:
            yield
            duration = time.time() - start_time
            self.record_task_complete(task_name, duration, status="success")
        except Exception as e:
            duration = time.time() - start_time
            error_type = type(e).__name__
            self.record_task_failure(task_name, error_type, duration)
            raise


# Global metrics instance (singleton pattern)
_global_metrics: PrometheusMetrics | None = None


def get_metrics() -> PrometheusMetrics | None:
    """Get global metrics instance.

    Returns:
        Global PrometheusMetrics instance or None if not initialized
    """
    return _global_metrics


def setup_metrics(
    app: Any = None,
    namespace: str = "aiotasks",
    enable_http_server: bool = False,
    http_port: int = 9090,
) -> PrometheusMetrics:
    """Setup global Prometheus metrics.

    Args:
        app: AioTasks application instance
        namespace: Metric namespace prefix
        enable_http_server: Auto-start HTTP metrics server
        http_port: HTTP server port

    Returns:
        PrometheusMetrics instance

    Usage:
        >>> from aiotasks import AioTasks
        >>> from aiotasks.monitoring import setup_metrics
        >>>
        >>> app = AioTasks('myapp', broker='redis://localhost')
        >>> metrics = setup_metrics(app, namespace='myapp', enable_http_server=True)
    """
    global _global_metrics

    if _global_metrics is not None:
        log.warning("Metrics already initialized, returning existing instance")
        return _global_metrics

    _global_metrics = PrometheusMetrics(
        app=app,
        namespace=namespace,
        enable_http_server=enable_http_server,
        http_port=http_port,
    )

    return _global_metrics
