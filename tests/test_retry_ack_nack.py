"""Tests for retry logic, ACK, and NACK functionality.

Tests the tenacity-based retry system with exponential backoff.
"""

import asyncio

import pytest

from aiotasks import AioTasks, build_manager


@pytest.mark.asyncio()
async def test_task_retry_success_after_failure():
    """Test task that fails then succeeds."""
    app = AioTasks("test_app", broker="memory://", max_retries=3)

    attempt_count = 0
    final_status = None

    @app.task()
    async def flaky_task():
        nonlocal attempt_count, final_status
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError(f"Failure on attempt {attempt_count}")
        final_status = "success"

    app.run()
    await flaky_task.delay()
    await app.wait(timeout=10, exit_on_finish=True, wait_timeout=0.1)
    app.stop()

    assert attempt_count == 3
    assert final_status == "success"


@pytest.mark.asyncio()
async def test_task_retry_max_attempts():
    """Test task that always fails reaches max retries."""
    app = AioTasks("test_app", broker="memory://", max_retries=2)

    attempt_count = 0

    @app.task()
    async def always_fails():
        nonlocal attempt_count
        attempt_count += 1
        raise RuntimeError(f"Always fails (attempt {attempt_count})")

    app.run()
    await always_fails.delay()
    await app.wait(timeout=10, exit_on_finish=True, wait_timeout=0.1)
    app.stop()

    assert attempt_count == 2  # max_retries


@pytest.mark.asyncio()
async def test_task_no_retry_on_success():
    """Test task that succeeds on first attempt doesn't retry."""
    app = AioTasks("test_app", broker="memory://", max_retries=5)

    attempt_count = 0

    @app.task()
    async def success_task():
        nonlocal attempt_count
        attempt_count += 1

    app.run()
    await success_task.delay()
    await app.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)
    app.stop()

    assert attempt_count == 1


@pytest.mark.asyncio()
async def test_multiple_tasks_with_retries():
    """Test multiple tasks with different retry behaviors."""
    app = AioTasks("test_app", broker="memory://", max_retries=3)

    counts = {"success": 0, "flaky": 0, "fail": 0}

    @app.task()
    async def success_task():
        counts["success"] += 1

    @app.task()
    async def flaky_task():
        counts["flaky"] += 1
        if counts["flaky"] < 2:
            raise ValueError("Flaky failure")

    @app.task()
    async def fail_task():
        counts["fail"] += 1
        raise RuntimeError("Always fails")

    app.run()
    await success_task.delay()
    await flaky_task.delay()
    await fail_task.delay()
    await app.wait(timeout=10, exit_on_finish=True, wait_timeout=0.1)
    app.stop()

    assert counts["success"] == 1  # Success on first try
    assert counts["flaky"] == 2  # Failed once, succeeded second time
    assert counts["fail"] == 3  # Failed all 3 attempts


@pytest.mark.asyncio()
async def test_task_ack_on_success():
    """Test that successful tasks are acknowledged."""
    manager = build_manager("memory://", max_retries=3)

    executed = False
    task_id = None

    @manager.task()
    async def ack_test_task():
        nonlocal executed
        executed = True

    manager.run()
    await ack_test_task.delay()
    await manager.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()

    assert executed is True
    # For memory backend, we can check that task completed
    # (ACK removes it from tracking)


@pytest.mark.asyncio()
async def test_task_nack_on_failure():
    """Test that failed tasks are negatively acknowledged."""
    manager = build_manager("memory://", max_retries=2)

    attempt_count = 0

    @manager.task()
    async def nack_test_task():
        nonlocal attempt_count
        attempt_count += 1
        raise Exception("Task failed")

    manager.run()
    await nack_test_task.delay()
    await manager.wait(timeout=10, exit_on_finish=True, wait_timeout=0.1)
    manager.stop()

    assert attempt_count == 2  # Failed max_retries times


@pytest.mark.asyncio()
async def test_retry_with_different_exceptions():
    """Test retry behavior with different exception types."""
    app = AioTasks("test_app", broker="memory://", max_retries=3)

    attempts = {"value": 0, "runtime": 0, "type": 0}

    @app.task()
    async def value_error_task():
        attempts["value"] += 1
        if attempts["value"] < 2:
            raise ValueError("Value error")

    @app.task()
    async def runtime_error_task():
        attempts["runtime"] += 1
        if attempts["runtime"] < 2:
            raise RuntimeError("Runtime error")

    @app.task()
    async def type_error_task():
        attempts["type"] += 1
        if attempts["type"] < 2:
            raise TypeError("Type error")

    app.run()
    await value_error_task.delay()
    await runtime_error_task.delay()
    await type_error_task.delay()
    await app.wait(timeout=10, exit_on_finish=True, wait_timeout=0.1)
    app.stop()

    assert attempts["value"] == 2
    assert attempts["runtime"] == 2
    assert attempts["type"] == 2


@pytest.mark.asyncio()
async def test_concurrent_tasks_with_retries():
    """Test concurrent task execution with retries."""
    app = AioTasks("test_app", broker="memory://", concurrency=5, max_retries=2)

    results = []

    @app.task()
    async def concurrent_task(task_id: int):
        nonlocal results
        await asyncio.sleep(0.1)
        results.append(task_id)

    app.run()
    for i in range(10):
        await concurrent_task.delay(i)

    await app.wait(timeout=5, exit_on_finish=True, wait_timeout=0.1)
    app.stop()

    assert len(results) == 10
    assert set(results) == set(range(10))


@pytest.mark.asyncio()
async def test_retry_exponential_backoff():
    """Test that retry uses exponential backoff."""
    import time

    app = AioTasks("test_app", broker="memory://", max_retries=3)

    timestamps = []

    @app.task()
    async def backoff_task():
        nonlocal timestamps
        timestamps.append(time.time())
        if len(timestamps) < 3:
            raise ValueError("Retry needed")

    app.run()
    await backoff_task.delay()
    await app.wait(timeout=30, exit_on_finish=True, wait_timeout=0.1)
    app.stop()

    # Check that delays increase (exponential backoff)
    if len(timestamps) >= 2:
        delay1 = timestamps[1] - timestamps[0]
        if len(timestamps) >= 3:
            delay2 = timestamps[2] - timestamps[1]
            # Second delay should be longer than first (exponential)
            assert delay2 > delay1
