"""AioTasks - Modern async task queue for Python 3.12+.

Provides both Celery-style API and classic API for distributed task processing.
"""

# Celery-style API (recommended)
from .app import AioTasks

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
