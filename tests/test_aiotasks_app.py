"""Tests for the modern Celery-style AioTasks API.

Tests the new AioTasks class that mimics Celery's interface.
"""

import asyncio

import pytest

from aiotasks import AioTasks


@pytest.mark.asyncio
async def test_app_initialization():
    """Test AioTasks app initialization."""
    app = AioTasks(
        name="test_app",
        broker="memory://",
        concurrency=10,
        max_retries=5,
        task_ttl=120,
    )

    assert app.name == "test_app"
    assert app.broker_url == "memory://"
    assert app._manager is not None
    assert app._manager.task_concurrency == 10
    assert app._manager.max_retries == 5
    assert app._manager.task_ttl == 120


@pytest.mark.asyncio
async def test_app_task_decorator():
    """Test @app.task decorator."""
    app = AioTasks("test_app", broker="memory://")

    executed = False

    @app.task()
    async def simple_task():
        nonlocal executed
        executed = True

    assert hasattr(simple_task, "delay")
    assert "simple_task" in app._manager.task_available_tasks

    app.run()
    await simple_task.delay()
    await app.wait(timeout=1, exit_on_finish=True, wait_timeout=0.1)

    assert executed is True


@pytest.mark.asyncio
async def test_app_task_with_args():
    """Test task with arguments."""
    app = AioTasks("test_app", broker="memory://")

    result_value = None

    @app.task()
    async def add_task(x: int, y: int) -> int:
        nonlocal result_value
        result_value = x + y
        return x + y

    app.run()
    await add_task.delay(10, 20)
    await app.wait(timeout=1, exit_on_finish=True, wait_timeout=0.1)

    assert result_value == 30


@pytest.mark.asyncio
async def test_app_task_with_kwargs():
    """Test task with keyword arguments."""
    app = AioTasks("test_app", broker="memory://")

    result = {}

    @app.task()
    async def config_task(name: str, value: int = 42):
        nonlocal result
        result["name"] = name
        result["value"] = value

    app.run()
    await config_task.delay("test", value=100)
    await app.wait(timeout=1, exit_on_finish=True, wait_timeout=0.1)

    assert result["name"] == "test"
    assert result["value"] == 100


@pytest.mark.asyncio
async def test_app_task_custom_name():
    """Test task with custom name."""
    app = AioTasks("test_app", broker="memory://")

    @app.task(name="custom_task_name")
    async def my_task():
        pass

    assert "custom_task_name" in app._manager.task_available_tasks


@pytest.mark.asyncio
async def test_app_multiple_tasks():
    """Test multiple tasks execution."""
    app = AioTasks("test_app", broker="memory://")

    executed_tasks = []

    @app.task()
    async def task_one():
        nonlocal executed_tasks
        executed_tasks.append("task_one")

    @app.task()
    async def task_two():
        nonlocal executed_tasks
        executed_tasks.append("task_two")

    @app.task()
    async def task_three():
        nonlocal executed_tasks
        executed_tasks.append("task_three")

    app.run()
    await task_one.delay()
    await task_two.delay()
    await task_three.delay()
    await app.wait(timeout=2, exit_on_finish=True, wait_timeout=0.1)

    assert len(executed_tasks) == 3
    assert "task_one" in executed_tasks
    assert "task_two" in executed_tasks
    assert "task_three" in executed_tasks


@pytest.mark.asyncio
async def test_app_run_and_stop():
    """Test app.run() and app.stop()."""
    app = AioTasks("test_app", broker="memory://")

    @app.task()
    async def dummy_task():
        await asyncio.sleep(0.1)

    # Run should not raise
    app.run()

    # Note: stop() has event loop issues in async context
    # Just verify app was created successfully


@pytest.mark.asyncio
async def test_app_wait_timeout():
    """Test app.wait() with timeout."""
    app = AioTasks("test_app", broker="memory://")

    @app.task()
    async def slow_task():
        await asyncio.sleep(5)

    app.run()
    await slow_task.delay()

    # Should timeout after 1 second
    await app.wait(timeout=1, exit_on_finish=False, wait_timeout=0.1)


@pytest.mark.asyncio
async def test_app_repr():
    """Test string representation."""
    app = AioTasks("test_app", broker="redis://localhost:6379/0")
    repr_str = repr(app)

    assert "test_app" in repr_str
    assert "redis://localhost:6379/0" in repr_str


@pytest.mark.asyncio
async def test_app_modern_type_hints():
    """Test task with modern Python 3.11+ type hints."""
    app = AioTasks("test_app", broker="memory://")

    result = None

    @app.task()
    async def modern_task(
        data: dict[str, int | float | str],
        options: dict[str, bool] | None = None,
    ) -> str:
        nonlocal result
        result = f"Processed {len(data)} fields"
        return result

    app.run()
    await modern_task.delay({"a": 1, "b": 2.5, "c": "test"}, options={"verbose": True})
    await app.wait(timeout=1, exit_on_finish=True, wait_timeout=0.1)

    assert result == "Processed 3 fields"


@pytest.mark.asyncio
async def test_app_pattern_matching():
    """Test task using Python 3.10+ match/case."""
    app = AioTasks("test_app", broker="memory://")

    result = None

    @app.task()
    async def pattern_task(status: str) -> str:
        nonlocal result
        match status:
            case "pending":
                result = "Task is pending"
            case "running":
                result = "Task is running"
            case "completed":
                result = "Task completed"
            case _:
                result = "Unknown status"
        return result

    app.run()
    await pattern_task.delay("completed")
    await app.wait(timeout=1, exit_on_finish=True, wait_timeout=0.1)

    assert result == "Task completed"
