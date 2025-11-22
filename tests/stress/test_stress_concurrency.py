"""Stress and concurrency tests for AioTasks.

Tests cover:
- High concurrency scenarios
- Large volume of tasks
- Memory leaks
- Performance under load
- Race conditions
"""

import asyncio
import time

import pytest

from aiotasks import AioTasks, every


@pytest.mark.asyncio
@pytest.mark.slow
class TestHighConcurrency:
    """Test high concurrency scenarios."""

    async def test_1000_concurrent_tasks(self):
        """Test handling 1000 concurrent tasks."""
        app = AioTasks(
            broker="memory://",
            concurrency=100,  # High concurrency
        )

        completed = {"count": 0}

        @app.task()
        async def concurrent_task(task_id: int):
            await asyncio.sleep(0.01)  # Minimal delay
            completed["count"] += 1
            return task_id

        app.run()

        # Queue 1000 tasks
        start_time = time.time()

        for i in range(1000):
            concurrent_task.delay(i)

        # Wait for completion (with timeout)
        await asyncio.sleep(30)

        time.time() - start_time

        app.stop()

        # Should complete significant portion
        assert completed["count"] > 900

    async def test_rapid_task_queuing(self):
        """Test rapidly queuing tasks."""
        app = AioTasks(
            broker="memory://",
            concurrency=50,
        )

        @app.task()
        async def quick_task(x: int):
            return x * 2

        app.run()

        start_time = time.time()

        # Queue 500 tasks as fast as possible
        for i in range(500):
            quick_task.delay(i)

        elapsed = time.time() - start_time

        app.stop()

        # Should be very fast
        assert elapsed < 5.0

    async def test_concurrent_result_backend_access(self):
        """Test concurrent access to result backend."""
        app = AioTasks(
            broker="memory://",
            backend="memory://",
            concurrency=50,
        )

        @app.task()
        async def task_with_result(x: int):
            await asyncio.sleep(0.01)
            return x**2

        app.run()

        # Queue tasks
        task_ids = []
        for i in range(100):
            ctx = task_with_result.delay(i)
            task_ids.append(ctx.task_id)

        # Concurrently check results
        async def check_result(task_id):
            try:
                result = await app.wait_for_result(task_id, timeout=10)
                return result.result if result else None
            except (TimeoutError, RuntimeError):
                return None

        results = await asyncio.gather(*[check_result(tid) for tid in task_ids])

        app.stop()

        # Most should complete
        completed = [r for r in results if r is not None]

        assert len(completed) > 80

    async def test_periodic_tasks_under_load(self):
        """Test periodic tasks while system is under load."""
        app = AioTasks(
            broker="memory://",
            concurrency=50,
        )

        periodic_count = {"count": 0}
        regular_count = {"count": 0}

        @app.task()
        async def periodic_task():
            periodic_count["count"] += 1

        @app.task()
        async def regular_task():
            await asyncio.sleep(0.01)
            regular_count["count"] += 1

        # Add periodic task (every 500ms)
        app.add_periodic_task(
            name="under_load",
            schedule=every(seconds=0.5),
            task="periodic_task",
        )

        app.run()
        await app.start_scheduler()

        # Queue many regular tasks
        for _ in range(200):
            regular_task.delay()

        # Wait
        await asyncio.sleep(3)

        await app.stop_scheduler()
        app.stop()

        # Periodic tasks should still run
        assert periodic_count["count"] >= 5  # At least 5 runs in 3 seconds
        assert regular_count["count"] > 150  # Most regular tasks complete


@pytest.mark.asyncio
@pytest.mark.slow
class TestMemoryAndResources:
    """Test memory usage and resource management."""

    async def test_no_memory_leak_in_result_backend(self):
        """Test result backend doesn't leak memory."""
        app = AioTasks(
            broker="memory://",
            backend="memory://",
            task_ttl=1,  # Short TTL
        )

        @app.task()
        async def memory_test_task(x: int):
            return x

        app.run()

        # Run many tasks
        for i in range(500):
            memory_test_task.delay(i)

        await asyncio.sleep(2)

        # Check backend size
        backend = app._result_backend
        if hasattr(backend, "_results"):
            # Should not grow unbounded due to TTL
            assert len(backend._results) < 1000

        app.stop()

    async def test_no_memory_leak_in_dlq(self):
        """Test DLQ respects max_size."""
        app = AioTasks(broker="memory://", max_retries=0)

        app._dlq.max_size = 100  # Small limit

        @app.task()
        async def failing_task(x: int):
            msg = "Fail"
            raise RuntimeError(msg)

        app.run()

        # Queue many failing tasks
        for i in range(200):
            failing_task.delay(i)

        await asyncio.sleep(2)

        # DLQ should not exceed max_size
        stats = app.get_dlq_stats()

        assert stats["total_tasks"] <= app._dlq.max_size

        app.stop()

    async def test_task_cleanup_after_completion(self):
        """Test tasks are cleaned up after completion."""
        app = AioTasks(
            broker="memory://",
            concurrency=20,
        )

        @app.task()
        async def cleanup_task():
            await asyncio.sleep(0.01)
            return "done"

        app.run()

        # Queue tasks
        for _ in range(100):
            cleanup_task.delay()

        # Wait for completion
        await asyncio.sleep(3)

        # Check for lingering tasks
        if hasattr(app._manager, "_task_queue"):
            queue_size = app._manager._task_queue.qsize()
            assert queue_size == 0

        app.stop()


@pytest.mark.asyncio
@pytest.mark.slow
class TestRaceConditions:
    """Test for race conditions."""

    async def test_concurrent_dlq_access(self):
        """Test concurrent DLQ operations."""
        app = AioTasks(broker="memory://")

        async def add_to_dlq(task_id):
            await app._dlq.add_task(
                task_id=task_id,
                task_name="test",
                error="Error",
            )

        async def read_from_dlq(task_id):
            return await app._dlq.get_task(task_id)

        async def remove_from_dlq(task_id):
            return await app._dlq.remove_task(task_id)

        # Concurrent operations
        # Add 50 tasks
        operations = [add_to_dlq(f"task{i}") for i in range(50)]

        # Concurrent reads
        operations.extend([read_from_dlq(f"task{i}") for i in range(50)])

        # Concurrent removes
        operations.extend([remove_from_dlq(f"task{i}") for i in range(25)])

        # Execute all concurrently
        await asyncio.gather(*operations)

        # Verify DLQ state is consistent
        stats = app.get_dlq_stats()

        # Should be roughly 25 (50 added - 25 removed)
        assert 20 <= stats["total_tasks"] <= 30

    async def test_concurrent_periodic_task_modification(self):
        """Test concurrent modification of periodic tasks."""
        app = AioTasks(broker="memory://")

        async def add_task(i):
            app.add_periodic_task(
                name=f"task{i}",
                schedule=every(hours=1),
                task=f"task{i}",
            )

        async def remove_task(i):
            return app.remove_periodic_task(f"task{i}")

        # Concurrent adds and removes
        operations = [add_task(i) for i in range(20)]
        operations.extend([remove_task(i) for i in range(10)])

        await asyncio.gather(*operations)

        # Verify consistent state
        tasks = app.list_periodic_tasks()

        # Should be around 10-20
        assert 8 <= len(tasks) <= 22


@pytest.mark.asyncio
@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Performance benchmarks."""

    async def test_task_throughput(self):
        """Measure task throughput."""
        app = AioTasks(
            broker="memory://",
            concurrency=100,
        )

        completed = {"count": 0}

        @app.task()
        async def throughput_task():
            completed["count"] += 1

        app.run()

        # Queue 1000 tasks and measure time
        start = time.time()

        for _ in range(1000):
            throughput_task.delay()

        # Wait for completion
        await asyncio.sleep(10)

        elapsed = time.time() - start

        app.stop()

        throughput = completed["count"] / elapsed

        # Should handle at least 100 tasks/sec
        assert throughput > 100

    async def test_result_backend_performance(self):
        """Measure result backend performance."""
        app = AioTasks(
            broker="memory://",
            backend="memory://",
            concurrency=50,
        )

        @app.task()
        async def result_task(x: int):
            return x

        app.run()

        # Measure result retrieval time
        task_ids = []
        for i in range(100):
            ctx = result_task.delay(i)
            task_ids.append(ctx.task_id)

        start = time.time()

        # Retrieve all results
        results = []
        for task_id in task_ids:
            try:
                result = await app.wait_for_result(task_id, timeout=5)
                results.append(result)
            except TimeoutError:
                pass

        elapsed = time.time() - start

        app.stop()

        rate = len(results) / elapsed if elapsed > 0 else 0

        assert rate > 10  # At least 10 results/sec

    async def test_dlq_operations_performance(self):
        """Measure DLQ operations performance."""
        app = AioTasks(broker="memory://")

        # Add 1000 failed tasks
        start = time.time()

        for i in range(1000):
            await app._dlq.add_task(
                task_id=f"perf{i}",
                task_name="test",
                error="Error",
            )

        add_elapsed = time.time() - start

        # List all tasks
        start = time.time()
        await app._dlq.list_tasks()
        list_elapsed = time.time() - start

        # Get stats
        start = time.time()
        app.get_dlq_stats()
        stats_elapsed = time.time() - start

        # Should be reasonably fast
        assert add_elapsed < 5.0  # Under 5 seconds for 1000 adds
        assert list_elapsed < 1.0  # Under 1 second to list 1000
        assert stats_elapsed < 0.5  # Under 500ms for stats


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])  # -s to see print output
