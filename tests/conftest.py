"""Shared pytest fixtures for aiotasks tests.

Modern Python 3.11+ fixtures using pytest-asyncio.
"""

import asyncio

import pytest
import pytest_asyncio

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy for all tests."""
    return asyncio.get_event_loop_policy()


@pytest_asyncio.fixture
async def memory_manager():
    """Fixture for memory-based task manager."""
    from aiotasks import build_manager

    manager = build_manager(
        dsn="memory://",
        prefix="test",
        concurrency=5,
        max_retries=3,
        task_ttl=60,
    )
    yield manager
    manager.stop()


@pytest_asyncio.fixture
async def memory_app():
    """Fixture for memory-based AioTasks app (Celery-style)."""
    from aiotasks import AioTasks

    app = AioTasks(
        name="test_app",
        broker="memory://",
        concurrency=5,
        max_retries=3,
        task_ttl=60,
    )
    yield app
    app.stop()


@pytest.fixture
def task_timeout() -> float:
    """Default timeout for task execution."""
    return 2.0


@pytest.fixture
def wait_timeout() -> float:
    """Default timeout for waiting between polls."""
    return 0.1
