"""Result Backend for storing and retrieving task results.

Provides storage backends for task results, compatible with Celery result backends.
Supports multiple storage backends: Redis, Memory, and can be extended.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

try:
    import ujson as json_lib
except ImportError:
    import json as json_lib

log = logging.getLogger("aiotasks")


class TaskResult:
    """Represents a task result with metadata."""

    def __init__(
        self,
        task_id: str,
        status: str,
        result: Any = None,
        error: str | None = None,
        traceback: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ):
        """Initialize task result.

        Args:
            task_id: Unique task identifier
            status: Task status (pending, started, success, failure, retry)
            result: Task return value (if successful)
            error: Error message (if failed)
            traceback: Full traceback (if failed)
            started_at: Task start timestamp
            completed_at: Task completion timestamp
        """
        self.task_id = task_id
        self.status = status
        self.result = result
        self.error = error
        self.traceback = traceback
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "traceback": self.traceback,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResult":
        """Create from dictionary."""
        started_at = (
            datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        )
        completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        )

        return cls(
            task_id=data["task_id"],
            status=data["status"],
            result=data.get("result"),
            error=data.get("error"),
            traceback=data.get("traceback"),
            started_at=started_at,
            completed_at=completed_at,
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"<TaskResult {self.task_id} status={self.status}>"


class ResultBackend(ABC):
    """Abstract base class for result backends."""

    def __init__(self, ttl: int = 3600):
        """Initialize result backend.

        Args:
            ttl: Time-to-live for results in seconds (default 1 hour)
        """
        self.ttl = ttl

    @abstractmethod
    async def store_result(self, task_id: str, result: TaskResult) -> None:
        """Store task result.

        Args:
            task_id: Task identifier
            result: Task result object
        """

    @abstractmethod
    async def get_result(self, task_id: str) -> TaskResult | None:
        """Get task result.

        Args:
            task_id: Task identifier

        Returns:
            Task result or None if not found
        """

    @abstractmethod
    async def delete_result(self, task_id: str) -> bool:
        """Delete task result.

        Args:
            task_id: Task identifier

        Returns:
            True if deleted, False if not found
        """

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
            TimeoutError: If timeout is reached
            RuntimeError: If task failed
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            result = await self.get_result(task_id)

            if result:
                if result.status == "success":
                    return result
                if result.status == "failure":
                    error_msg = f"Task {task_id} failed: {result.error}"
                    raise RuntimeError(error_msg)

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                msg = f"Timeout waiting for result of task {task_id}"
                raise TimeoutError(msg)

            await asyncio.sleep(poll_interval)


class MemoryResultBackend(ResultBackend):
    """In-memory result backend for testing/development."""

    def __init__(self, ttl: int = 3600):
        """Initialize memory result backend."""
        super().__init__(ttl)
        self._results: dict[str, TaskResult] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def store_result(self, task_id: str, result: TaskResult) -> None:
        """Store result in memory."""
        self._results[task_id] = result

        # Start cleanup task if not running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Get result from memory."""
        return self._results.get(task_id)

    async def delete_result(self, task_id: str) -> bool:
        """Delete result from memory."""
        if task_id in self._results:
            del self._results[task_id]
            return True
        return False

    async def _cleanup_expired(self) -> None:
        """Clean up expired results."""
        while True:
            await asyncio.sleep(60)  # Check every minute

            now = datetime.utcnow()
            expired = []

            for task_id, result in self._results.items():
                if result.completed_at:
                    age = (now - result.completed_at).total_seconds()
                    if age > self.ttl:
                        expired.append(task_id)

            for task_id in expired:
                del self._results[task_id]
                log.debug(f"Cleaned up expired result for task {task_id}")

            if not self._results:
                break  # Stop cleanup if no results


class RedisResultBackend(ResultBackend):
    """Redis-based result backend for production use."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl: int = 3600,
        key_prefix: str = "aiotasks:result:",
    ):
        """Initialize Redis result backend.

        Args:
            redis_url: Redis connection URL
            ttl: Time-to-live for results in seconds
            key_prefix: Prefix for Redis keys
        """
        super().__init__(ttl)
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis = None

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
            except ImportError:
                msg = "redis package required for RedisResultBackend"
                raise ImportError(msg) from None

            self._redis = await aioredis.from_url(self.redis_url)

        return self._redis

    def _make_key(self, task_id: str) -> str:
        """Create Redis key for task result."""
        return f"{self.key_prefix}{task_id}"

    async def store_result(self, task_id: str, result: TaskResult) -> None:
        """Store result in Redis."""
        redis = await self._get_redis()
        key = self._make_key(task_id)

        # Serialize result
        data = json_lib.dumps(result.to_dict())

        # Store with TTL
        await redis.setex(key, self.ttl, data)

        log.debug(f"Stored result for task {task_id} in Redis (TTL: {self.ttl}s)")

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Get result from Redis."""
        redis = await self._get_redis()
        key = self._make_key(task_id)

        data = await redis.get(key)
        if data is None:
            return None

        # Deserialize result
        result_dict = json_lib.loads(data)
        return TaskResult.from_dict(result_dict)

    async def delete_result(self, task_id: str) -> bool:
        """Delete result from Redis."""
        redis = await self._get_redis()
        key = self._make_key(task_id)

        deleted = await redis.delete(key)
        return deleted > 0

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


def build_result_backend(
    backend: str | None = None,
    ttl: int = 3600,
    **kwargs: Any,
) -> ResultBackend | None:
    """Build result backend from DSN.

    Args:
        backend: Backend DSN (redis://..., memory://, or None)
        ttl: Time-to-live for results in seconds
        **kwargs: Additional backend-specific arguments

    Returns:
        Result backend instance or None if backend is None

    Examples:
        >>> backend = build_result_backend("redis://localhost:6379/1")
        >>> backend = build_result_backend("memory://")
        >>> backend = build_result_backend(None)  # No result backend
    """
    if backend is None or backend == "":
        return None

    if backend.startswith("memory://"):
        return MemoryResultBackend(ttl=ttl)

    if backend.startswith("redis://"):
        return RedisResultBackend(redis_url=backend, ttl=ttl, **kwargs)

    msg = f"Unsupported result backend: {backend}"
    raise ValueError(msg)
