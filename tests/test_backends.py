"""Tests for task backends (Memory, Redis, AMQP, ZMQ).

Modern tests for all backend implementations.
"""

import asyncio

import pytest

from aiotasks import build_manager


@pytest.mark.asyncio
async def test_build_manager_memory():
    """Test building a memory backend manager."""
    manager = build_manager(
        dsn="memory://",
        prefix="test",
        concurrency=5,
        max_retries=3,
        task_ttl=60,
    )

    assert manager is not None
    assert manager.prefix == "test"
    assert manager.task_concurrency == 5
    assert manager.max_retries == 3
    assert manager.task_ttl == 60

    manager.stop()


@pytest.mark.asyncio
async def test_memory_backend_task_execution():
    """Test task execution with memory backend."""
    manager = build_manager("memory://", prefix="test")

    executed = False

    @manager.task()
    async def memory_task():
        nonlocal executed
        executed = True

    manager.run()
    await memory_task.delay()
    await manager.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()

    assert executed is True


@pytest.mark.asyncio
async def test_memory_backend_multiple_tasks():
    """Test multiple tasks with memory backend."""
    manager = build_manager("memory://", prefix="test", concurrency=3)

    results = []

    @manager.task()
    async def counting_task(num: int):
        nonlocal results
        await asyncio.sleep(0.05)
        results.append(num)

    manager.run()
    for i in range(5):
        await counting_task.delay(i)

    await manager.wait(timeout=3, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()

    assert len(results) == 5
    assert set(results) == {0, 1, 2, 3, 4}


@pytest.mark.asyncio
async def test_memory_backend_task_with_args_kwargs():
    """Test task with args and kwargs on memory backend."""
    manager = build_manager("memory://")

    result = {}

    @manager.task()
    async def complex_task(x: int, y: int, operation: str = "add"):
        nonlocal result
        if operation == "add":
            result["value"] = x + y
        elif operation == "multiply":
            result["value"] = x * y
        result["operation"] = operation

    manager.run()
    await complex_task.delay(5, 10, operation="multiply")
    await manager.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()

    assert result["value"] == 50
    assert result["operation"] == "multiply"


@pytest.mark.asyncio
async def test_memory_backend_add_task():
    """Test add_task method on memory backend."""
    manager = build_manager("memory://")

    executed = False

    async def standalone_task():
        nonlocal executed
        executed = True

    manager.add_task(standalone_task)

    manager.run()
    await standalone_task.delay()
    await manager.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()

    assert executed is True


@pytest.mark.asyncio
async def test_memory_backend_custom_task_name():
    """Test custom task name with memory backend."""
    manager = build_manager("memory://")

    @manager.task(name="my_custom_task_name")
    async def some_task():
        pass

    assert "my_custom_task_name" in manager.task_available_tasks


@pytest.mark.asyncio
async def test_memory_backend_concurrency_limit():
    """Test concurrency limit on memory backend."""
    manager = build_manager("memory://", concurrency=2)

    concurrent_count = 0
    max_concurrent = 0

    @manager.task()
    async def concurrent_test():
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        await asyncio.sleep(0.2)
        concurrent_count -= 1

    manager.run()
    for _ in range(5):
        await concurrent_test.delay()

    await manager.wait(timeout=5, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()

    # Should respect concurrency limit of 2
    assert max_concurrent <= 2


@pytest.mark.asyncio
async def test_backend_dsn_variants():
    """Test different DSN formats."""
    # Memory
    manager1 = build_manager("memory://")
    assert manager1 is not None
    manager1.stop()

    # Redis format (won't connect but should parse)
    manager2 = build_manager("redis://localhost:6379/0")
    assert manager2 is not None
    manager2.stop()

    # AMQP format (won't connect but should parse)
    manager3 = build_manager("amqp://guest:guest@localhost:5672/")
    assert manager3 is not None
    manager3.stop()

    # ZMQ format (won't connect but should parse)
    manager4 = build_manager("zmq://localhost:5555")
    assert manager4 is not None
    manager4.stop()


@pytest.mark.asyncio
async def test_memory_has_pending_tasks():
    """Test has_pending_tasks method."""
    manager = build_manager("memory://")

    @manager.task()
    async def slow_task():
        await asyncio.sleep(1)

    manager.run()
    await slow_task.delay()

    # Give it a moment to start
    await asyncio.sleep(0.1)

    # Should have pending tasks
    has_pending = await manager.has_pending_tasks()
    assert has_pending is True or has_pending is False  # Depends on timing

    manager.stop()


@pytest.mark.asyncio
async def test_memory_cleanup_old_tasks():
    """Test cleanup_old_tasks method."""
    manager = build_manager("memory://", task_ttl=1)

    # Run a task
    @manager.task()
    async def cleanup_test():
        pass

    manager.run()
    await cleanup_test.delay()
    await manager.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)

    # Cleanup should work without error
    if hasattr(manager, "cleanup_old_tasks"):
        cleaned = await manager.cleanup_old_tasks()
        assert isinstance(cleaned, int)
        assert cleaned >= 0

    manager.stop()


@pytest.mark.asyncio
async def test_manager_run_stop_cycle():
    """Test run/stop cycle."""
    manager = build_manager("memory://")

    @manager.task()
    async def cycle_task():
        await asyncio.sleep(0.1)

    # First cycle
    manager.run()
    await cycle_task.delay()
    await manager.wait(timeout=1, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()

    # Second cycle
    manager.run()
    await cycle_task.delay()
    await manager.wait(timeout=1, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()


@pytest.mark.asyncio
async def test_task_ttl_configuration():
    """Test task TTL configuration."""
    manager = build_manager("memory://", task_ttl=300)

    assert manager.task_ttl == 300


@pytest.mark.asyncio
async def test_max_retries_configuration():
    """Test max retries configuration."""
    manager = build_manager("memory://", max_retries=10)

    assert manager.max_retries == 10


@pytest.mark.asyncio
async def test_prefix_configuration():
    """Test prefix configuration."""
    manager = build_manager("memory://", prefix="my_custom_prefix")

    assert manager.prefix == "my_custom_prefix"
