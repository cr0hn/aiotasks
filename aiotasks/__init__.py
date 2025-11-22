"""AioTasks - Modern async task queue for Python 3.12+.

Provides both Celery-style API and classic API for distributed task processing.
"""

# Celery-style API (recommended)
# Legacy imports (for backward compatibility)
from .actions import *  # noqa: F403
from .app import AioTasks
from .core import *  # noqa: F403

# Dashboard
from .dashboard import DashboardServer, create_dashboard

# Dead Letter Queue
from .dlq import DeadLetterQueue, FailedTask, RedisDLQ
from .helpers import *  # noqa: F403

# Monitoring and metrics
from .monitoring import PrometheusMetrics, get_metrics, setup_metrics

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

# Result backend
from .result_backend import (
    MemoryResultBackend,
    RedisResultBackend,
    ResultBackend,
    TaskResult,
    build_result_backend,
)
from .tasks import *  # noqa: F403

# Classic API (still supported)
from .tasks import build_manager

__version__ = "2.0.0"

__all__ = (
    "AioTasks",  # Modern Celery-style API
    "build_manager",  # Classic API
)
