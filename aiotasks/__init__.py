"""AioTasks - Modern async task queue for Python 3.12+.

Provides both Celery-style API and classic API for distributed task processing.
"""

# Celery-style API (recommended)
from .app import AioTasks

# Result backend
from .result_backend import (
    MemoryResultBackend,
    RedisResultBackend,
    ResultBackend,
    TaskResult,
    build_result_backend,
)

# Periodic tasks (Celery Beat compatible)
from .periodic import (
    CrontabSchedule,
    IntervalSchedule,
    PeriodicScheduler,
    PeriodicTask,
    Schedule,
    crontab,
    every,
)

# Dead Letter Queue
from .dlq import DeadLetterQueue, FailedTask, RedisDLQ

# Monitoring and metrics
from .monitoring import PrometheusMetrics, get_metrics, setup_metrics

# Rate limiting
from .rate_limit import (
    MemoryRateLimiter,
    RateLimit,
    RateLimitedTask,
    RateLimiter,
    RedisRateLimiter,
    build_rate_limiter,
    rate_limit,
)

# Dashboard
from .dashboard import DashboardServer, create_dashboard

# Classic API (still supported)
from .tasks import build_manager

# Legacy imports (for backward compatibility)
from .actions import *  # noqa: F403
from .core import *  # noqa: F403
from .helpers import *  # noqa: F403
from .tasks import *  # noqa: F403

__version__ = "2.0.0"

__all__ = (
    "AioTasks",  # Modern Celery-style API
    "build_manager",  # Classic API
)
