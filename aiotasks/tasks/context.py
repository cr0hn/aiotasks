"""Context managers for async task execution."""

import abc
import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

from ..core.exceptions import AioTasksTimeout

log = logging.getLogger("aiotasks")


class AsyncWaitContextManager:
    """Context manager for delayed task execution with timeout support."""

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the context manager.

        Args:
            args[0]: The coroutine function to execute
            args[1]: The list/queue name for the task
            args[2]: The poller/connection object
            args[3]: The function name for identification
            args[4:]: Additional positional arguments for the function
            **kwargs: Keyword arguments including timeout settings
        """
        if len(args) < 4:
            msg = "AsyncWaitContextManager requires at least 4 positional arguments"
            raise ValueError(msg)

        self.fn: Callable[..., Coroutine[Any, Any, Any]] = args[0]  # type: ignore[misc]
        self.list_name: str = args[1]
        self.poller: Any = args[2]
        self.function_name: str = args[3]
        self.timeout: float = kwargs.pop("timeout", 0)
        self.infinite_timeout: float = kwargs.pop("infinite_timeout", 900)

        self.args: tuple[Any, ...] = args[4:]
        self.kwargs: dict[str, Any] = kwargs

    @abc.abstractmethod
    def __await__(self) -> Any:  # pragma: no cover
        """Await implementation for direct task submission."""
        raise NotImplementedError

    async def __aenter__(self) -> Any:
        """Enter the context manager and execute the task with timeout.

        Returns:
            The result of the coroutine function

        Raises:
            AioTasksTimeout: If the task execution exceeds the timeout
        """
        try:
            timeout = self.timeout if self.timeout else self.infinite_timeout
            return await asyncio.wait_for(
                self.fn(*self.args, **self.kwargs),
                timeout=timeout,
            )
        except TimeoutError as e:
            log.error("%s: %s", self.fn.__name__, e)
            raise AioTasksTimeout(str(e)) from e

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the context manager."""

    def build_delay_message(
        self,
        task_id: str | None = None,
        function_name: str | None = None,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> bytes:
        """Build a message for delayed task execution.

        Args:
            task_id: Unique identifier for the task (generated if not provided)
            function_name: Name of the function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function

        Returns:
            Serialized message as bytes
        """
        if task_id is None:
            task_id = uuid.uuid4().hex

        if function_name is None:
            function_name = self.function_name

        if args is None:
            args = self.args

        if kwargs is None:
            kwargs = self.kwargs

        return msgpack.packb(
            {
                "task_id": task_id,
                "function": function_name,
                "args": args,
                "kwargs": kwargs,
            },
            use_bin_type=True,
        )


__all__ = ("AsyncWaitContextManager",)
