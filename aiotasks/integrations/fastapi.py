"""FastAPI integration for aiotasks.

This module provides seamless integration between aiotasks and FastAPI,
making it easy to run background tasks in FastAPI applications.

Example:
    ```python
    from fastapi import FastAPI
    from aiotasks.integrations.fastapi import AioTasksMiddleware, setup_aiotasks

    app = FastAPI()

    # Setup aiotasks with FastAPI
    setup_aiotasks(app, dsn="redis://localhost:6379/0")

    # Define tasks
    @app.state.aiotasks.task()
    async def send_email(to: str, subject: str, body: str):
        # Send email logic
        await asyncio.sleep(2)
        print(f"Email sent to {to}")

    # Use tasks in endpoints
    @app.post("/send-email")
    async def create_email_task(to: str, subject: str, body: str):
        await send_email.delay(to, subject, body)
        return {"status": "Task queued"}
    ```
"""

import contextlib
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..tasks.backends import build_manager
from ..tasks.bases import AsyncTaskBase

log = logging.getLogger("aiotasks")


class AioTasksMiddleware(BaseHTTPMiddleware):
    """Middleware to manage aiotasks lifecycle in FastAPI.

    This middleware ensures the task manager is properly started and stopped
    with the FastAPI application lifecycle.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and ensure aiotasks is available.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain

        Returns:
            The HTTP response
        """
        # Make manager available in request state
        if hasattr(request.app.state, "aiotasks"):
            request.state.aiotasks = request.app.state.aiotasks

        return await call_next(request)


def setup_aiotasks(
    app: FastAPI,
    dsn: str = "memory://",
    prefix: str = "aiotasks",
    auto_start: bool = True,
    **kwargs: Any,
) -> AsyncTaskBase:
    """Setup aiotasks with a FastAPI application.

    This function integrates aiotasks with FastAPI by:
    1. Creating a task manager
    2. Storing it in app.state
    3. Setting up startup/shutdown event handlers
    4. Adding middleware for request-level access

    Args:
        app: The FastAPI application instance
        dsn: Data Source Name for the backend
            - "memory://" for in-memory (development)
            - "redis://host:port/db" for Redis (production)
            - "amqp://user:pass@host/" for RabbitMQ
            - "zmq://host:port" for ZeroMQ
        prefix: Prefix for all task names and channels
        auto_start: Automatically start task processing on startup
        **kwargs: Additional backend-specific arguments

    Returns:
        The configured task manager instance

    Examples:
        >>> from fastapi import FastAPI
        >>> from aiotasks.integrations.fastapi import setup_aiotasks
        >>>
        >>> app = FastAPI()
        >>> manager = setup_aiotasks(app, dsn="redis://localhost:6379/0")
        >>>
        >>> @manager.task()
        >>> async def process_data(data_id: int):
        >>>     # Process data asynchronously
        >>>     pass
    """
    # Create task manager
    manager = build_manager(dsn=dsn, prefix=prefix, **kwargs)

    # Store in app state
    app.state.aiotasks = manager

    # Add middleware
    app.add_middleware(AioTasksMiddleware)

    # Setup lifecycle event handlers
    @app.on_event("startup")
    async def start_aiotasks() -> None:
        """Start aiotasks when FastAPI starts."""
        if auto_start:
            log.info("Starting aiotasks manager")
            manager.run()
            log.info("AioTasks manager started successfully")

    @app.on_event("shutdown")
    async def stop_aiotasks() -> None:
        """Stop aiotasks when FastAPI shuts down."""
        log.info("Stopping aiotasks manager")
        with contextlib.suppress(Exception):
            manager.stop()
        log.info("AioTasks manager stopped")

    return manager


@contextlib.asynccontextmanager
async def aiotasks_lifespan(
    app: FastAPI,
    dsn: str = "memory://",
    prefix: str = "aiotasks",
    **kwargs: Any,
) -> AsyncIterator[dict[str, Any]]:
    """Modern lifespan context manager for FastAPI with aiotasks.

    This is the recommended way to integrate aiotasks with FastAPI 0.109+
    using the new lifespan parameter.

    Args:
        app: The FastAPI application instance
        dsn: Data Source Name for the backend
        prefix: Prefix for all task names and channels
        **kwargs: Additional backend-specific arguments

    Yields:
        Dictionary with the manager instance

    Examples:
        >>> from contextlib import asynccontextmanager
        >>> from fastapi import FastAPI
        >>> from aiotasks.integrations.fastapi import aiotasks_lifespan
        >>>
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        >>>     async with aiotasks_lifespan(
        >>>         app,
        >>>         dsn="redis://localhost:6379/0"
        >>>     ) as state:
        >>>         yield state
        >>>
        >>> app = FastAPI(lifespan=lifespan)
        >>>
        >>> @app.state.aiotasks.task()
        >>> async def my_task(x: int):
        >>>     return x * 2
    """
    # Create and start manager
    manager = build_manager(dsn=dsn, prefix=prefix, **kwargs)
    app.state.aiotasks = manager

    log.info("Starting aiotasks manager")
    manager.run()

    try:
        yield {"aiotasks": manager}
    finally:
        log.info("Stopping aiotasks manager")
        with contextlib.suppress(Exception):
            manager.stop()


def get_aiotasks(request: Request) -> AsyncTaskBase:
    """Dependency to get aiotasks manager in FastAPI endpoints.

    Args:
        request: The FastAPI request object

    Returns:
        The aiotasks manager instance

    Raises:
        RuntimeError: If aiotasks is not configured

    Examples:
        >>> from fastapi import Depends, FastAPI
        >>> from aiotasks.integrations.fastapi import get_aiotasks, setup_aiotasks
        >>>
        >>> app = FastAPI()
        >>> setup_aiotasks(app, dsn="redis://localhost:6379/0")
        >>>
        >>> @app.get("/queue-task")
        >>> async def queue_task(manager = Depends(get_aiotasks)):
        >>>     # Use manager to queue tasks
        >>>     await manager.some_task.delay(arg1, arg2)
        >>>     return {"status": "queued"}
    """
    if not hasattr(request.app.state, "aiotasks"):
        msg = "AioTasks not configured. Call setup_aiotasks(app) first."
        raise RuntimeError(msg)

    return request.app.state.aiotasks


__all__ = (
    "AioTasksMiddleware",
    "aiotasks_lifespan",
    "get_aiotasks",
    "setup_aiotasks",
)
