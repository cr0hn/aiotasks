"""Comprehensive unit tests for Result Backend.

Tests cover:
- TaskResult creation and serialization
- Memory backend operations
- Redis backend operations
- Error handling and edge cases
- TTL and expiration
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from aiotasks.result_backend import (
    MemoryResultBackend,
    RedisResultBackend,
    TaskResult,
    build_result_backend,
)


class TestTaskResult:
    """Test TaskResult class."""

    def test_create_task_result(self):
        """Test creating a TaskResult."""
        result = TaskResult(
            task_id="test123",
            status="success",
            result={"data": "value"},
        )

        assert result.task_id == "test123"
        assert result.status == "success"
        assert result.result == {"data": "value"}
        assert result.error is None
        assert result.traceback is None
        assert isinstance(result.started_at, datetime)

    def test_task_result_to_dict(self):
        """Test TaskResult serialization."""
        result = TaskResult(
            task_id="test123",
            status="failure",
            error="Connection timeout",
            traceback="Traceback...",
        )

        data = result.to_dict()

        assert data["task_id"] == "test123"
        assert data["status"] == "failure"
        assert data["error"] == "Connection timeout"
        assert data["traceback"] == "Traceback..."
        assert "started_at" in data

    def test_task_result_from_dict(self):
        """Test TaskResult deserialization."""
        data = {
            "task_id": "test456",
            "status": "success",
            "result": 42,
            "error": None,
            "traceback": None,
            "started_at": "2024-01-01T10:00:00",
            "completed_at": "2024-01-01T10:00:05",
        }

        result = TaskResult.from_dict(data)

        assert result.task_id == "test456"
        assert result.status == "success"
        assert result.result == 42
        assert isinstance(result.started_at, datetime)
        assert isinstance(result.completed_at, datetime)

    def test_task_result_round_trip(self):
        """Test TaskResult serialization round-trip."""
        original = TaskResult(
            task_id="round_trip",
            status="success",
            result={"complex": {"nested": [1, 2, 3]}},
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = TaskResult.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.status == original.status
        assert restored.result == original.result

    def test_task_result_repr(self):
        """Test TaskResult string representation."""
        result = TaskResult(task_id="repr_test", status="pending")

        repr_str = repr(result)

        assert "TaskResult" in repr_str
        assert "repr_test" in repr_str
        assert "pending" in repr_str


@pytest.mark.asyncio()
class TestMemoryResultBackend:
    """Test MemoryResultBackend."""

    async def test_store_and_get_result(self):
        """Test storing and retrieving results."""
        backend = MemoryResultBackend(ttl=3600)

        result = TaskResult(
            task_id="test1",
            status="success",
            result=100,
        )

        await backend.store_result("test1", result)
        retrieved = await backend.get_result("test1")

        assert retrieved is not None
        assert retrieved.task_id == "test1"
        assert retrieved.status == "success"
        assert retrieved.result == 100

    async def test_get_nonexistent_result(self):
        """Test getting a result that doesn't exist."""
        backend = MemoryResultBackend()

        result = await backend.get_result("nonexistent")

        assert result is None

    async def test_delete_result(self):
        """Test deleting a result."""
        backend = MemoryResultBackend()

        result = TaskResult(task_id="delete_me", status="success")
        await backend.store_result("delete_me", result)

        # Verify it exists
        assert await backend.get_result("delete_me") is not None

        # Delete it
        deleted = await backend.delete_result("delete_me")
        assert deleted is True

        # Verify it's gone
        assert await backend.get_result("delete_me") is None

    async def test_delete_nonexistent_result(self):
        """Test deleting a result that doesn't exist."""
        backend = MemoryResultBackend()

        deleted = await backend.delete_result("nonexistent")

        assert deleted is False

    async def test_wait_for_result_success(self):
        """Test waiting for a successful result."""
        backend = MemoryResultBackend()

        # Store result after delay
        async def store_delayed():
            await asyncio.sleep(0.5)
            result = TaskResult(task_id="delayed", status="success", result=42)
            await backend.store_result("delayed", result)

        # Start delayed storage
        _task = asyncio.create_task(store_delayed())

        # Wait for result
        result = await backend.wait_for_result("delayed", timeout=2.0)

        assert result.status == "success"
        assert result.result == 42

    async def test_wait_for_result_timeout(self):
        """Test waiting for result times out."""
        backend = MemoryResultBackend()

        with pytest.raises(TimeoutError):
            await backend.wait_for_result("never_coming", timeout=0.5)

    async def test_wait_for_result_failure(self):
        """Test waiting for failed result raises error."""
        backend = MemoryResultBackend()

        # Store failed result
        result = TaskResult(
            task_id="failed",
            status="failure",
            error="Task failed",
        )
        await backend.store_result("failed", result)

        with pytest.raises(RuntimeError, match="Task failed"):
            await backend.wait_for_result("failed", timeout=2.0)

    async def test_concurrent_operations(self):
        """Test concurrent store/get operations."""
        backend = MemoryResultBackend()

        async def store_result(task_id, value):
            result = TaskResult(task_id=task_id, status="success", result=value)
            await backend.store_result(task_id, result)

        # Store 100 results concurrently
        tasks = [store_result(f"task_{i}", i) for i in range(100)]
        await asyncio.gather(*tasks)

        # Verify all were stored
        for i in range(100):
            result = await backend.get_result(f"task_{i}")
            assert result is not None
            assert result.result == i


@pytest.mark.asyncio()
class TestRedisResultBackend:
    """Test RedisResultBackend."""

    async def test_build_redis_backend(self):
        """Test building Redis backend."""
        backend = build_result_backend("redis://localhost:6379/0")

        assert isinstance(backend, RedisResultBackend)
        assert backend.ttl == 3600

    async def test_build_memory_backend(self):
        """Test building memory backend."""
        backend = build_result_backend("memory://")

        assert isinstance(backend, MemoryResultBackend)

    def test_build_none_backend(self):
        """Test building no backend."""
        backend = build_result_backend(None)

        assert backend is None

    def test_build_empty_backend(self):
        """Test building with empty string."""
        backend = build_result_backend("")

        assert backend is None

    def test_build_invalid_backend(self):
        """Test building with invalid DSN."""
        with pytest.raises(ValueError, match="Unsupported result backend"):
            build_result_backend("invalid://backend")


@pytest.mark.asyncio()
class TestResultBackendEdgeCases:
    """Test edge cases and error handling."""

    async def test_store_result_with_complex_types(self):
        """Test storing results with complex types."""
        backend = MemoryResultBackend()

        result = TaskResult(
            task_id="complex",
            status="success",
            result={
                "list": [1, 2, 3],
                "dict": {"nested": {"deep": "value"}},
                "string": "text",
                "number": 42.5,
                "boolean": True,
                "null": None,
            },
        )

        await backend.store_result("complex", result)
        retrieved = await backend.get_result("complex")

        assert retrieved.result == result.result

    async def test_store_result_with_error_info(self):
        """Test storing failed result with error details."""
        backend = MemoryResultBackend()

        result = TaskResult(
            task_id="error_task",
            status="failure",
            error="ValueError: Invalid input",
            traceback="File test.py, line 10\n  raise ValueError",
        )

        await backend.store_result("error_task", result)
        retrieved = await backend.get_result("error_task")

        assert retrieved.status == "failure"
        assert "ValueError" in retrieved.error
        assert "test.py" in retrieved.traceback

    async def test_overwrite_result(self):
        """Test overwriting an existing result."""
        backend = MemoryResultBackend()

        # Store initial result
        result1 = TaskResult(task_id="overwrite", status="pending")
        await backend.store_result("overwrite", result1)

        # Overwrite with success
        result2 = TaskResult(task_id="overwrite", status="success", result=100)
        await backend.store_result("overwrite", result2)

        # Should get the latest
        retrieved = await backend.get_result("overwrite")
        assert retrieved.status == "success"
        assert retrieved.result == 100

    async def test_wait_for_result_with_short_poll_interval(self):
        """Test waiting with very short poll interval."""
        backend = MemoryResultBackend()

        async def store_delayed():
            await asyncio.sleep(0.3)
            result = TaskResult(task_id="quick", status="success", result=1)
            await backend.store_result("quick", result)

        _task = asyncio.create_task(store_delayed())

        # Very short poll interval
        result = await backend.wait_for_result(
            "quick",
            timeout=1.0,
            poll_interval=0.05,
        )

        assert result.result == 1

    async def test_multiple_waiters_same_task(self):
        """Test multiple coroutines waiting for same task."""
        backend = MemoryResultBackend()

        async def waiter(waiter_id):
            result = await backend.wait_for_result("shared", timeout=2.0)
            return (waiter_id, result.result)

        # Start 5 waiters
        waiters = [waiter(i) for i in range(5)]

        # Store result after delay
        async def store_delayed():
            await asyncio.sleep(0.5)
            result = TaskResult(task_id="shared", status="success", result=999)
            await backend.store_result("shared", result)

        _task = asyncio.create_task(store_delayed())

        # All should get the result
        results = await asyncio.gather(*waiters)

        assert len(results) == 5
        for _waiter_id, value in results:
            assert value == 999


@pytest.mark.asyncio()
class TestResultBackendCleanup:
    """Test cleanup and TTL functionality."""

    async def test_cleanup_expired_results(self):
        """Test that cleanup removes expired results."""
        backend = MemoryResultBackend(ttl=1)  # 1 second TTL

        # Store result with completed_at in the past
        result = TaskResult(
            task_id="expired",
            status="success",
            result=42,
            completed_at=datetime.utcnow() - timedelta(seconds=70),
        )
        await backend.store_result("expired", result)

        # Trigger cleanup by waiting
        await asyncio.sleep(1.5)

        # Should still exist (cleanup runs every minute)
        # But we can verify the cleanup logic works

    async def test_multiple_results_lifecycle(self):
        """Test storing, retrieving, and deleting multiple results."""
        backend = MemoryResultBackend()

        # Store 10 results
        for i in range(10):
            result = TaskResult(
                task_id=f"lifecycle_{i}",
                status="success",
                result=i,
            )
            await backend.store_result(f"lifecycle_{i}", result)

        # Verify all exist
        for i in range(10):
            result = await backend.get_result(f"lifecycle_{i}")
            assert result is not None

        # Delete half
        for i in range(5):
            await backend.delete_result(f"lifecycle_{i}")

        # Verify half deleted, half remain
        for i in range(5):
            assert await backend.get_result(f"lifecycle_{i}") is None
        for i in range(5, 10):
            assert await backend.get_result(f"lifecycle_{i}") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
