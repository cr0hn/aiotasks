"""Comprehensive unit tests for Dead Letter Queue.

Tests cover:
- FailedTask creation and serialization
- DeadLetterQueue operations
- Task retry functionality
- DLQ statistics
- Error handling and edge cases
"""

import asyncio
from datetime import datetime

import pytest

from aiotasks.dlq import DeadLetterQueue, FailedTask


class TestFailedTask:
    """Test FailedTask class."""

    def test_create_failed_task(self):
        """Test creating a FailedTask."""
        task = FailedTask(
            task_id="failed123",
            task_name="process_data",
            args=(1, 2),
            kwargs={"key": "value"},
            error="Connection timeout",
            traceback="Traceback...",
            retry_count=3,
        )

        assert task.task_id == "failed123"
        assert task.task_name == "process_data"
        assert task.args == (1, 2)
        assert task.kwargs == {"key": "value"}
        assert task.error == "Connection timeout"
        assert task.traceback == "Traceback..."
        assert task.retry_count == 3
        assert isinstance(task.failed_at, datetime)

    def test_failed_task_to_dict(self):
        """Test FailedTask serialization."""
        task = FailedTask(
            task_id="test123",
            task_name="send_email",
            args=("user@example.com",),
            kwargs={"subject": "Test"},
            error="SMTP error",
        )

        data = task.to_dict()

        assert data["task_id"] == "test123"
        assert data["task_name"] == "send_email"
        assert data["args"] == ["user@example.com"]
        assert data["kwargs"] == {"subject": "Test"}
        assert data["error"] == "SMTP error"
        assert "failed_at" in data

    def test_failed_task_from_dict(self):
        """Test FailedTask deserialization."""
        data = {
            "task_id": "test456",
            "task_name": "process",
            "args": [1, 2, 3],
            "kwargs": {"flag": True},
            "error": "Error message",
            "traceback": "Full traceback",
            "retry_count": 5,
            "failed_at": "2024-01-01T10:00:00",
            "original_queue": "default",
        }

        task = FailedTask.from_dict(data)

        assert task.task_id == "test456"
        assert task.task_name == "process"
        assert task.args == (1, 2, 3)
        assert task.kwargs == {"flag": True}
        assert task.retry_count == 5
        assert isinstance(task.failed_at, datetime)

    def test_failed_task_round_trip(self):
        """Test FailedTask serialization round-trip."""
        original = FailedTask(
            task_id="round_trip",
            task_name="task",
            args=(1, "two", 3.0),
            kwargs={"nested": {"data": [1, 2, 3]}},
            error="Error",
            retry_count=2,
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = FailedTask.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.task_name == original.task_name
        assert restored.args == original.args
        assert restored.kwargs == original.kwargs
        assert restored.error == original.error
        assert restored.retry_count == original.retry_count

    def test_failed_task_repr(self):
        """Test FailedTask string representation."""
        task = FailedTask(
            task_id="repr_test",
            task_name="test_task",
            retry_count=3,
        )

        repr_str = repr(task)

        assert "FailedTask" in repr_str
        assert "repr_test" in repr_str
        assert "test_task" in repr_str
        assert "retries=3" in repr_str


@pytest.mark.asyncio()
class TestDeadLetterQueue:
    """Test DeadLetterQueue class."""

    async def test_create_dlq(self):
        """Test creating a DLQ."""
        dlq = DeadLetterQueue(prefix="test", max_size=1000)

        assert dlq.prefix == "test"
        assert dlq.max_size == 1000
        assert len(dlq._tasks) == 0

    async def test_add_failed_task(self):
        """Test adding a failed task to DLQ."""
        dlq = DeadLetterQueue()

        await dlq.add_task(
            task_id="failed1",
            task_name="send_email",
            args=("user@example.com",),
            error="Connection refused",
            retry_count=3,
        )

        task = await dlq.get_task("failed1")

        assert task is not None
        assert task.task_id == "failed1"
        assert task.task_name == "send_email"
        assert task.args == ("user@example.com",)
        assert task.error == "Connection refused"
        assert task.retry_count == 3

    async def test_get_nonexistent_task(self):
        """Test getting a task that doesn't exist."""
        dlq = DeadLetterQueue()

        task = await dlq.get_task("nonexistent")

        assert task is None

    async def test_list_tasks_empty(self):
        """Test listing tasks when DLQ is empty."""
        dlq = DeadLetterQueue()

        tasks = await dlq.list_tasks()

        assert tasks == []

    async def test_list_tasks_with_tasks(self):
        """Test listing tasks."""
        dlq = DeadLetterQueue()

        # Add 3 tasks
        await dlq.add_task("task1", "process", error="Error 1")
        await dlq.add_task("task2", "send_email", error="Error 2")
        await dlq.add_task("task3", "process", error="Error 3")

        tasks = await dlq.list_tasks()

        assert len(tasks) == 3

    async def test_list_tasks_with_limit(self):
        """Test listing tasks with limit."""
        dlq = DeadLetterQueue()

        # Add 5 tasks
        for i in range(5):
            await dlq.add_task(f"task{i}", "process", error=f"Error {i}")

        tasks = await dlq.list_tasks(limit=2)

        assert len(tasks) == 2

    async def test_list_tasks_filtered_by_name(self):
        """Test filtering tasks by name."""
        dlq = DeadLetterQueue()

        await dlq.add_task("task1", "send_email", error="Error 1")
        await dlq.add_task("task2", "process", error="Error 2")
        await dlq.add_task("task3", "send_email", error="Error 3")

        email_tasks = await dlq.list_tasks(task_name="send_email")

        assert len(email_tasks) == 2
        assert all(t.task_name == "send_email" for t in email_tasks)

    async def test_list_tasks_sorted_by_failed_at(self):
        """Test that tasks are sorted by failed_at (newest first)."""
        dlq = DeadLetterQueue()

        # Add tasks with delays to ensure different timestamps
        await dlq.add_task("task1", "process", error="First")
        await asyncio.sleep(0.01)
        await dlq.add_task("task2", "process", error="Second")
        await asyncio.sleep(0.01)
        await dlq.add_task("task3", "process", error="Third")

        tasks = await dlq.list_tasks()

        # Should be sorted newest first
        assert tasks[0].task_id == "task3"
        assert tasks[1].task_id == "task2"
        assert tasks[2].task_id == "task1"

    async def test_remove_task(self):
        """Test removing a task from DLQ."""
        dlq = DeadLetterQueue()

        await dlq.add_task("remove_me", "process", error="Error")

        # Verify it exists
        assert await dlq.get_task("remove_me") is not None

        # Remove it
        removed = await dlq.remove_task("remove_me")

        assert removed is True
        assert await dlq.get_task("remove_me") is None

    async def test_remove_nonexistent_task(self):
        """Test removing a task that doesn't exist."""
        dlq = DeadLetterQueue()

        removed = await dlq.remove_task("nonexistent")

        assert removed is False

    async def test_clear_all_tasks(self):
        """Test clearing all tasks."""
        dlq = DeadLetterQueue()

        # Add multiple tasks
        for i in range(5):
            await dlq.add_task(f"task{i}", "process", error="Error")

        # Clear all
        count = await dlq.clear()

        assert count == 5
        assert len(await dlq.list_tasks()) == 0

    async def test_clear_tasks_by_name(self):
        """Test clearing tasks by name."""
        dlq = DeadLetterQueue()

        await dlq.add_task("task1", "send_email", error="Error")
        await dlq.add_task("task2", "process", error="Error")
        await dlq.add_task("task3", "send_email", error="Error")

        count = await dlq.clear(task_name="send_email")

        assert count == 2
        remaining = await dlq.list_tasks()
        assert len(remaining) == 1
        assert remaining[0].task_name == "process"

    async def test_max_size_limit(self):
        """Test that DLQ respects max_size limit."""
        dlq = DeadLetterQueue(max_size=5)

        # Add 10 tasks (exceeds max_size)
        for i in range(10):
            await dlq.add_task(f"task{i}", "process", error=f"Error {i}")

        tasks = await dlq.list_tasks()

        # Should have at most max_size tasks
        assert len(tasks) <= 5


@pytest.mark.asyncio()
class TestDLQRetry:
    """Test DLQ retry functionality."""

    async def test_retry_single_task(self):
        """Test retrying a single failed task."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        dlq = DeadLetterQueue()

        execution_count = {"count": 0}

        @app.task()
        async def retryable_task(x: int):
            execution_count["count"] += 1
            return x * 2

        # Add failed task
        await dlq.add_task(
            task_id="retry1",
            task_name="retryable_task",
            args=(5,),
            error="Previous failure",
            retry_count=3,
        )

        # Start worker
        app.run()

        # Retry the task
        success = await dlq.retry_task("retry1", app)

        assert success is True

        # Task should be removed from DLQ
        assert await dlq.get_task("retry1") is None

        # Wait for execution
        await asyncio.sleep(0.5)
        app.stop()

        # Should have been executed
        assert execution_count["count"] > 0

    async def test_retry_nonexistent_task(self):
        """Test retrying a task that doesn't exist."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        dlq = DeadLetterQueue()

        success = await dlq.retry_task("nonexistent", app)

        assert success is False

    async def test_retry_all_tasks(self):
        """Test retrying all failed tasks."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        dlq = DeadLetterQueue()

        @app.task()
        async def task1():
            return "done"

        # Add multiple failed tasks
        for i in range(3):
            await dlq.add_task(f"task{i}", "task1", error="Error")

        app.run()

        # Retry all
        count = await dlq.retry_all(app)

        assert count == 3

        # All should be removed from DLQ
        remaining = await dlq.list_tasks()
        assert len(remaining) == 0

        app.stop()

    async def test_retry_all_with_filter(self):
        """Test retrying filtered tasks."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        dlq = DeadLetterQueue()

        @app.task()
        async def send_email():
            return "sent"

        @app.task()
        async def process_data():
            return "processed"

        # Add mixed failed tasks
        await dlq.add_task("email1", "send_email", error="Error")
        await dlq.add_task("process1", "process_data", error="Error")
        await dlq.add_task("email2", "send_email", error="Error")

        app.run()

        # Retry only email tasks
        count = await dlq.retry_all(app, task_name="send_email")

        assert count == 2

        # Only process task should remain
        remaining = await dlq.list_tasks()
        assert len(remaining) == 1
        assert remaining[0].task_name == "process_data"

        app.stop()

    async def test_retry_all_with_limit(self):
        """Test retrying with limit."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        dlq = DeadLetterQueue()

        @app.task()
        async def task1():
            return "done"

        # Add 5 failed tasks
        for i in range(5):
            await dlq.add_task(f"task{i}", "task1", error="Error")

        app.run()

        # Retry only 2
        count = await dlq.retry_all(app, limit=2)

        assert count == 2

        # 3 should remain
        remaining = await dlq.list_tasks()
        assert len(remaining) == 3

        app.stop()


@pytest.mark.asyncio()
class TestDLQStatistics:
    """Test DLQ statistics."""

    def test_get_stats_empty_dlq(self):
        """Test getting stats from empty DLQ."""
        dlq = DeadLetterQueue()

        stats = dlq.get_stats()

        assert stats["total_tasks"] == 0
        assert stats["max_size"] == 10000
        assert stats["by_task_name"] == {}
        assert stats["oldest_failure"] is None
        assert stats["newest_failure"] is None

    async def test_get_stats_with_tasks(self):
        """Test getting stats with tasks."""
        dlq = DeadLetterQueue()

        # Add various tasks
        await dlq.add_task("task1", "send_email", error="Error")
        await dlq.add_task("task2", "send_email", error="Error")
        await dlq.add_task("task3", "process_data", error="Error")

        stats = dlq.get_stats()

        assert stats["total_tasks"] == 3
        assert stats["by_task_name"]["send_email"] == 2
        assert stats["by_task_name"]["process_data"] == 1
        assert stats["oldest_failure"] is not None
        assert stats["newest_failure"] is not None

    async def test_stats_after_operations(self):
        """Test stats after various operations."""
        dlq = DeadLetterQueue()

        # Add tasks
        for i in range(10):
            await dlq.add_task(f"task{i}", "process", error="Error")

        # Remove some
        await dlq.remove_task("task0")
        await dlq.remove_task("task1")

        # Clear some by name (but we only have one name)
        # Add a different task type first
        await dlq.add_task("email1", "send_email", error="Error")
        await dlq.clear(task_name="send_email")

        stats = dlq.get_stats()

        assert stats["total_tasks"] == 8  # 10 - 2 removed - 0 cleared
        assert "send_email" not in stats["by_task_name"]


@pytest.mark.asyncio()
class TestDLQEdgeCases:
    """Test edge cases for DLQ."""

    async def test_add_task_with_complex_args(self):
        """Test adding task with complex arguments."""
        dlq = DeadLetterQueue()

        await dlq.add_task(
            task_id="complex",
            task_name="task",
            args=([1, 2, 3], {"nested": "dict"}),
            kwargs={"list": [4, 5, 6], "dict": {"key": "value"}},
            error="Error",
        )

        task = await dlq.get_task("complex")

        assert task.args == ([1, 2, 3], {"nested": "dict"})
        assert task.kwargs == {"list": [4, 5, 6], "dict": {"key": "value"}}

    async def test_add_duplicate_task_id(self):
        """Test adding task with duplicate ID (should overwrite)."""
        dlq = DeadLetterQueue()

        await dlq.add_task("dup", "task1", error="First error")
        await dlq.add_task("dup", "task2", error="Second error")

        task = await dlq.get_task("dup")

        # Should have the latest version
        assert task.task_name == "task2"
        assert task.error == "Second error"

    async def test_concurrent_operations(self):
        """Test concurrent DLQ operations."""
        dlq = DeadLetterQueue()

        async def add_tasks(start, count):
            for i in range(start, start + count):
                await dlq.add_task(f"task{i}", "process", error="Error")

        # Add tasks concurrently
        await asyncio.gather(
            add_tasks(0, 10),
            add_tasks(10, 10),
            add_tasks(20, 10),
        )

        tasks = await dlq.list_tasks()

        assert len(tasks) == 30

    async def test_retry_task_with_missing_function(self):
        """Test retrying task when function doesn't exist."""
        from aiotasks import AioTasks

        app = AioTasks(broker="memory://")
        dlq = DeadLetterQueue()

        await dlq.add_task(
            task_id="missing",
            task_name="nonexistent_task",
            args=(),
            error="Error",
        )

        app.run()

        success = await dlq.retry_task("missing", app)

        # Should fail gracefully
        assert success is False

        # Task should still be in DLQ
        assert await dlq.get_task("missing") is not None

        app.stop()

    async def test_empty_task_name_filter(self):
        """Test filtering with empty task name."""
        dlq = DeadLetterQueue()

        await dlq.add_task("task1", "process", error="Error")

        # Filter with None should return all
        tasks = await dlq.list_tasks(task_name=None)

        assert len(tasks) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
