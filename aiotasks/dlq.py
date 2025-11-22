"""Dead Letter Queue (DLQ) for failed tasks.

Provides storage and management for tasks that have failed all retry attempts.
Allows inspection, debugging, and manual retry of failed tasks.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

log = logging.getLogger("aiotasks")


@dataclass
class FailedTask:
    """Represents a task that has failed all retries."""

    task_id: str
    task_name: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    error: str | None = None
    traceback: str | None = None
    retry_count: int = 0
    failed_at: datetime = field(default_factory=datetime.utcnow)
    original_queue: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "args": list(self.args),
            "kwargs": self.kwargs,
            "error": self.error,
            "traceback": self.traceback,
            "retry_count": self.retry_count,
            "failed_at": self.failed_at.isoformat(),
            "original_queue": self.original_queue,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FailedTask":
        """Create from dictionary."""
        failed_at = (
            datetime.fromisoformat(data["failed_at"])
            if "failed_at" in data
            else datetime.utcnow()
        )

        return cls(
            task_id=data["task_id"],
            task_name=data["task_name"],
            args=tuple(data.get("args", [])),
            kwargs=data.get("kwargs", {}),
            error=data.get("error"),
            traceback=data.get("traceback"),
            retry_count=data.get("retry_count", 0),
            failed_at=failed_at,
            original_queue=data.get("original_queue"),
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"<FailedTask {self.task_id} task={self.task_name} retries={self.retry_count}>"


class DeadLetterQueue:
    """Dead letter queue for failed tasks.

    Stores tasks that have failed all retry attempts for later inspection
    and potential manual retry.

    Example:
        >>> dlq = DeadLetterQueue(prefix="myapp")
        >>>
        >>> # Add failed task
        >>> await dlq.add_task(failed_task)
        >>>
        >>> # List failed tasks
        >>> failed = await dlq.list_tasks()
        >>>
        >>> # Retry specific task
        >>> await dlq.retry_task(task_id, app)
    """

    def __init__(
        self,
        prefix: str = "aiotasks",
        max_size: int = 10000,
    ):
        """Initialize DLQ.

        Args:
            prefix: Prefix for DLQ storage keys
            max_size: Maximum number of failed tasks to store
        """
        self.prefix = prefix
        self.max_size = max_size
        self._tasks: dict[str, FailedTask] = {}

    async def add_task(
        self,
        task_id: str,
        task_name: str,
        args: tuple = (),
        kwargs: dict | None = None,
        error: str | None = None,
        traceback: str | None = None,
        retry_count: int = 0,
        original_queue: str | None = None,
    ) -> None:
        """Add failed task to DLQ.

        Args:
            task_id: Task identifier
            task_name: Task function name
            args: Task positional arguments
            kwargs: Task keyword arguments
            error: Error message
            traceback: Full traceback
            retry_count: Number of retry attempts made
            original_queue: Original queue name
        """
        if kwargs is None:
            kwargs = {}

        # Check size limit
        if len(self._tasks) >= self.max_size:
            log.warning(
                f"DLQ size limit reached ({self.max_size}), removing oldest task"
            )
            # Remove oldest task
            oldest = min(self._tasks.values(), key=lambda t: t.failed_at)
            del self._tasks[oldest.task_id]

        failed_task = FailedTask(
            task_id=task_id,
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            error=error,
            traceback=traceback,
            retry_count=retry_count,
            failed_at=datetime.utcnow(),
            original_queue=original_queue,
        )

        self._tasks[task_id] = failed_task

        log.warning(
            f"Task {task_id} ({task_name}) added to DLQ after {retry_count} retries: {error}"
        )

    async def get_task(self, task_id: str) -> FailedTask | None:
        """Get failed task by ID.

        Args:
            task_id: Task identifier

        Returns:
            FailedTask or None if not found
        """
        return self._tasks.get(task_id)

    async def list_tasks(
        self,
        limit: int | None = None,
        task_name: str | None = None,
    ) -> list[FailedTask]:
        """List failed tasks.

        Args:
            limit: Maximum number of tasks to return
            task_name: Filter by task name (optional)

        Returns:
            List of failed tasks, sorted by failed_at (newest first)
        """
        tasks = list(self._tasks.values())

        # Filter by task name if specified
        if task_name:
            tasks = [t for t in tasks if t.task_name == task_name]

        # Sort by failed_at (newest first)
        tasks.sort(key=lambda t: t.failed_at, reverse=True)

        # Apply limit
        if limit:
            tasks = tasks[:limit]

        return tasks

    async def remove_task(self, task_id: str) -> bool:
        """Remove task from DLQ.

        Args:
            task_id: Task identifier

        Returns:
            True if removed, False if not found
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            log.info(f"Removed task {task_id} from DLQ")
            return True

        return False

    async def clear(self, task_name: str | None = None) -> int:
        """Clear DLQ.

        Args:
            task_name: Clear only tasks with this name (optional)

        Returns:
            Number of tasks removed
        """
        if task_name is None:
            count = len(self._tasks)
            self._tasks.clear()
            log.info(f"Cleared DLQ ({count} tasks removed)")
            return count

        # Clear only specific task type
        to_remove = [
            task_id
            for task_id, task in self._tasks.items()
            if task.task_name == task_name
        ]

        for task_id in to_remove:
            del self._tasks[task_id]

        log.info(f"Cleared {len(to_remove)} tasks with name '{task_name}' from DLQ")
        return len(to_remove)

    async def retry_task(self, task_id: str, app: Any) -> bool:
        """Retry failed task.

        Args:
            task_id: Task identifier
            app: AioTasks application instance

        Returns:
            True if task was queued for retry, False if not found

        Example:
            >>> # Retry specific task
            >>> success = await dlq.retry_task("abc123", app)
            >>> if success:
            ...     print("Task queued for retry")
        """
        task = await self.get_task(task_id)
        if task is None:
            log.warning(f"Task {task_id} not found in DLQ")
            return False

        try:
            # Get task function from app
            if not hasattr(app, "_manager"):
                log.error("Cannot retry task: app has no manager")
                return False

            task_func = app._manager.task_available_tasks.get(task.task_name)
            if task_func is None:
                log.error(f"Task function not found: {task.task_name}")
                return False

            # Queue the task again
            if hasattr(task_func, "delay"):
                await task_func.delay(*task.args, **task.kwargs)
                log.info(f"Task {task_id} ({task.task_name}) queued for retry")

                # Remove from DLQ
                await self.remove_task(task_id)
                return True

            log.error(f"Task {task.task_name} does not have delay() method")
            return False

        except Exception as e:
            log.exception(f"Error retrying task {task_id}: {e}")
            return False

    async def retry_all(
        self,
        app: Any,
        task_name: str | None = None,
        limit: int | None = None,
    ) -> int:
        """Retry multiple failed tasks.

        Args:
            app: AioTasks application instance
            task_name: Retry only tasks with this name (optional)
            limit: Maximum number of tasks to retry (optional)

        Returns:
            Number of tasks successfully queued for retry

        Example:
            >>> # Retry all failed email tasks
            >>> count = await dlq.retry_all(app, task_name="send_email")
            >>> print(f"Retried {count} tasks")
        """
        tasks = await self.list_tasks(limit=limit, task_name=task_name)

        success_count = 0
        for task in tasks:
            if await self.retry_task(task.task_id, app):
                success_count += 1

        log.info(f"Retried {success_count}/{len(tasks)} failed tasks")
        return success_count

    def get_stats(self) -> dict[str, Any]:
        """Get DLQ statistics.

        Returns:
            Dictionary with DLQ stats

        Example:
            >>> stats = dlq.get_stats()
            >>> print(f"Total failed tasks: {stats['total_tasks']}")
        """
        task_counts: dict[str, int] = {}
        for task in self._tasks.values():
            task_counts[task.task_name] = task_counts.get(task.task_name, 0) + 1

        return {
            "total_tasks": len(self._tasks),
            "max_size": self.max_size,
            "by_task_name": task_counts,
            "oldest_failure": (
                min(t.failed_at for t in self._tasks.values()).isoformat()
                if self._tasks
                else None
            ),
            "newest_failure": (
                max(t.failed_at for t in self._tasks.values()).isoformat()
                if self._tasks
                else None
            ),
        }


class RedisDLQ(DeadLetterQueue):
    """Redis-based DLQ for production use.

    Stores failed tasks in Redis for persistence across restarts.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "aiotasks",
        max_size: int = 10000,
        key_prefix: str = "dlq:",
    ):
        """Initialize Redis DLQ.

        Args:
            redis_url: Redis connection URL
            prefix: Prefix for app
            max_size: Maximum number of failed tasks to store
            key_prefix: Prefix for Redis keys
        """
        super().__init__(prefix=prefix, max_size=max_size)
        self.redis_url = redis_url
        self.key_prefix = f"{prefix}:{key_prefix}"
        self._redis = None

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
            except ImportError:
                msg = "redis package required for RedisDLQ"
                raise ImportError(msg) from None

            self._redis = await aioredis.from_url(self.redis_url)

        return self._redis

    def _make_key(self, task_id: str) -> str:
        """Create Redis key for failed task."""
        return f"{self.key_prefix}{task_id}"

    async def add_task(
        self,
        task_id: str,
        task_name: str,
        args: tuple = (),
        kwargs: dict | None = None,
        error: str | None = None,
        traceback: str | None = None,
        retry_count: int = 0,
        original_queue: str | None = None,
    ) -> None:
        """Add failed task to Redis DLQ."""
        redis = await self._get_redis()

        failed_task = FailedTask(
            task_id=task_id,
            task_name=task_name,
            args=args,
            kwargs=kwargs or {},
            error=error,
            traceback=traceback,
            retry_count=retry_count,
            failed_at=datetime.utcnow(),
            original_queue=original_queue,
        )

        # Store in Redis
        key = self._make_key(task_id)
        data = json.dumps(failed_task.to_dict())
        await redis.set(key, data)

        # Add to sorted set for ordering
        await redis.zadd(
            f"{self.key_prefix}index",
            {task_id: failed_task.failed_at.timestamp()},
        )

        log.warning(
            f"Task {task_id} ({task_name}) added to Redis DLQ after {retry_count} retries"
        )

    async def get_task(self, task_id: str) -> FailedTask | None:
        """Get failed task from Redis."""
        redis = await self._get_redis()
        key = self._make_key(task_id)

        data = await redis.get(key)
        if data is None:
            return None

        task_dict = json.loads(data)
        return FailedTask.from_dict(task_dict)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


__all__ = (
    "FailedTask",
    "DeadLetterQueue",
    "RedisDLQ",
)
