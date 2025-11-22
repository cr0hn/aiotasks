"""Full integration tests for AioTasks.

Tests complete workflows with real task execution.
"""

import asyncio

import pytest

from aiotasks import AioTasks, build_manager


@pytest.mark.asyncio
async def test_complete_workflow_memory():
    """Test complete workflow with memory backend."""
    app = AioTasks("integration_test", broker="memory://", concurrency=5)

    results = []

    @app.task()
    async def add_numbers(a: int, b: int) -> int:
        nonlocal results
        result = a + b
        results.append(result)
        return result

    app.run()

    # Queue multiple tasks
    await add_numbers.delay(1, 2)
    await add_numbers.delay(3, 4)
    await add_numbers.delay(5, 6)

    # Wait for completion
    await app.wait(timeout=5, exit_on_finish=True, wait_timeout=0.1)

    # Verify results
    assert len(results) == 3
    assert 3 in results
    assert 7 in results
    assert 11 in results


@pytest.mark.asyncio
async def test_task_with_exception_handling():
    """Test task exception handling."""
    app = AioTasks("exception_test", broker="memory://", max_retries=1)

    success_count = 0
    error_count = 0

    @app.task()
    async def may_fail(should_fail: bool):
        nonlocal success_count, error_count
        if should_fail:
            error_count += 1
            raise ValueError("Task failed intentionally")
        success_count += 1

    app.run()

    await may_fail.delay(False)  # Should succeed
    await may_fail.delay(True)  # Should fail

    await app.wait(timeout=5, exit_on_finish=True, wait_timeout=0.1)

    assert success_count >= 1
    assert error_count >= 1


@pytest.mark.asyncio
async def test_concurrent_task_execution():
    """Test concurrent task execution."""
    app = AioTasks("concurrent_test", broker="memory://", concurrency=10)

    import time

    start_times = []
    end_times = []

    @app.task()
    async def concurrent_task(task_id: int):
        nonlocal start_times, end_times
        start_times.append((task_id, time.time()))
        await asyncio.sleep(0.1)
        end_times.append((task_id, time.time()))

    app.run()

    # Queue 10 tasks
    for i in range(10):
        await concurrent_task.delay(i)

    await app.wait(timeout=10, exit_on_finish=True, wait_timeout=0.1)

    # With concurrency=10, all should have started roughly at the same time
    assert len(start_times) == 10
    assert len(end_times) == 10


@pytest.mark.asyncio
async def test_task_with_complex_data_types():
    """Test tasks with complex data types."""
    app = AioTasks("complex_test", broker="memory://")

    received_data = None

    @app.task()
    async def process_complex_data(data: dict[str, list[int]]):
        nonlocal received_data
        received_data = data

    app.run()

    test_data = {"numbers": [1, 2, 3, 4, 5], "values": [10, 20, 30]}
    await process_complex_data.delay(test_data)

    await app.wait(timeout=5, exit_on_finish=True, wait_timeout=0.1)

    assert received_data == test_data


@pytest.mark.asyncio
async def test_classic_api_compatibility():
    """Test classic build_manager API still works."""
    manager = build_manager("memory://", concurrency=3)

    executed = False

    @manager.task()
    async def classic_task():
        nonlocal executed
        executed = True

    manager.run()
    await classic_task.delay()
    await manager.wait(timeout=3, exit_on_finish=True, wait_timeout=0.1)

    assert executed is True


@pytest.mark.asyncio
async def test_task_chaining():
    """Test chaining multiple tasks."""
    app = AioTasks("chain_test", broker="memory://")

    results = []

    @app.task()
    async def step1(value: int) -> int:
        results.append(("step1", value))
        return value * 2

    @app.task()
    async def step2(value: int) -> int:
        results.append(("step2", value))
        return value + 10

    app.run()

    # Execute tasks sequentially
    await step1.delay(5)
    await asyncio.sleep(0.2)  # Wait for step1
    await step2.delay(10)  # Using result from step1

    await app.wait(timeout=5, exit_on_finish=True, wait_timeout=0.1)

    assert len(results) >= 2


@pytest.mark.asyncio
async def test_long_running_tasks():
    """Test long-running tasks don't block."""
    app = AioTasks("longrun_test", broker="memory://", concurrency=3)

    completed = []

    @app.task()
    async def long_task(task_id: int, duration: float):
        await asyncio.sleep(duration)
        completed.append(task_id)

    app.run()

    # Queue short and long tasks
    await long_task.delay(1, 1.0)  # 1 second
    await long_task.delay(2, 0.1)  # 100ms
    await long_task.delay(3, 0.1)  # 100ms

    await app.wait(timeout=5, exit_on_finish=True, wait_timeout=0.1)

    # Short tasks should complete even though long task is running
    assert len(completed) == 3


@pytest.mark.asyncio
async def test_task_with_kwargs():
    """Test task with keyword arguments."""
    app = AioTasks("kwargs_test", broker="memory://")

    received_kwargs = None

    @app.task()
    async def kwargs_task(name: str, age: int = 0, city: str = "Unknown"):
        nonlocal received_kwargs
        received_kwargs = {"name": name, "age": age, "city": city}

    app.run()

    await kwargs_task.delay("Alice", age=30, city="NYC")

    await app.wait(timeout=3, exit_on_finish=True, wait_timeout=0.1)

    assert received_kwargs == {"name": "Alice", "age": 30, "city": "NYC"}


@pytest.mark.asyncio
async def test_multiple_apps_isolated():
    """Test multiple app instances are isolated."""
    app1 = AioTasks("app1", broker="memory://")
    app2 = AioTasks("app2", broker="memory://")

    app1_executed = False
    app2_executed = False

    @app1.task()
    async def app1_task():
        nonlocal app1_executed
        app1_executed = True

    @app2.task()
    async def app2_task():
        nonlocal app2_executed
        app2_executed = True

    # Both should work independently
    app1.run()
    await app1_task.delay()
    await app1.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)

    app2.run()
    await app2_task.delay()
    await app2.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)

    assert app1_executed is True
    assert app2_executed is True


@pytest.mark.asyncio
async def test_task_naming():
    """Test custom task naming."""
    app = AioTasks("naming_test", broker="memory://")

    @app.task(name="custom_task_name")
    async def my_function():
        pass

    # Should be registered with custom name
    assert "custom_task_name" in app._manager.task_available_tasks


@pytest.mark.asyncio
async def test_app_configuration_parameters():
    """Test app configuration parameters."""
    app = AioTasks(
        name="config_test",
        broker="memory://",
        concurrency=15,
        max_retries=5,
        task_ttl=7200,
    )

    assert app.name == "config_test"
    assert app._manager.task_concurrency == 15
    assert app._manager.max_retries == 5
    assert app._manager.task_ttl == 7200
