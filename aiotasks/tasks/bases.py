"""Base classes for asyncio-based task management system.

This module provides abstract base classes for building asynchronous task
management systems with publish/subscribe patterns and delayed task execution.
"""

import abc
import asyncio
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger("aiotasks")


# -------------------------------------------------------------------------
# Base classes
# -------------------------------------------------------------------------
class AsyncTaskSubscribeBase(metaclass=abc.ABCMeta):
    """Abstract base class for asynchronous task subscription and topic handling.

    This class provides the foundation for implementing publish/subscribe patterns
    in asyncio applications. It manages topic subscriptions, message handling,
    and task execution for subscribed topics.

    Attributes:
        prefix: Namespace prefix for topics.
        running_tasks: Dictionary of currently running tasks.
        topics_subscribers: Mapping of topics to their subscriber functions.
        subscriber_ready: Event indicating subscriber is ready to receive messages.
    """

    def __init__(self, prefix: str = "aiotasks") -> None:
        """Initialize the subscription base.

        Args:
            prefix: Namespace prefix for topics. Defaults to "aiotasks".
        """
        self.prefix = prefix

        self.running_tasks: dict[str, asyncio.Task] = dict()
        self.topics_subscribers: dict[str, set[Callable]] = defaultdict(set)
        self.subscriber_ready = asyncio.Event()

    def subscribe(self, topics: str | set[str] | None = None) -> Callable:
        """Decorator to register coroutine functions as topic subscribers.

        Args:
            topics: Single topic string or set of topic strings to subscribe to.
                   If None, creates an empty set.

        Returns:
            Decorator function that registers the coroutine as a subscriber.

        Example:
            >>> @manager.subscribe("my_topic")
            >>> async def handle_message(topic, data):
            ...     print(f"Received: {data}")
        """
        if not topics:
            topics = set()

        if isinstance(topics, str):
            topics = {topics}

        def real_decorator(f: Callable) -> Callable:
            # if function is a coro, add some new functions
            if asyncio.iscoroutinefunction(f):
                if not topics:
                    log.error(f"Empty topic fount in function '{f.__name__}'. Skipping " "it.")
                for topic in topics:
                    self.topics_subscribers[topic].add(f)
            return f

        return real_decorator

    @abc.abstractmethod
    async def wait_for_message(self, channel: Any) -> bool:  # pragma: no cover
        """Wait for a message to arrive on the channel.

        Args:
            channel: The channel object to wait on.

        Returns:
            True if a message is available, False otherwise.
        """
        pass

    @abc.abstractmethod
    async def get_next_message(self, channel: Any) -> object:  # pragma: no cover
        """Retrieve the next message from the channel.

        Args:
            channel: The channel object to read from.

        Returns:
            The next message from the channel.
        """
        pass

    @abc.abstractmethod
    async def register_topics(self) -> Any:  # pragma: no cover
        """Register subscribed topics with the messaging backend.

        Returns:
            Channel object for receiving messages.
        """
        pass

    @abc.abstractmethod
    async def publish(self, topic: str, info: Any) -> None:  # pragma: no cover
        """Publish a message to a topic.

        Args:
            topic: The topic to publish to.
            info: The message data to publish.
        """
        pass

    @abc.abstractmethod
    async def has_pending_topics(self) -> bool:  # pragma: no cover
        """Check if there are any pending topic messages.

        Returns:
            True if there are pending messages, False otherwise.
        """
        pass

    def _make_tasks_done_subscriber(self, task_id: str, future: asyncio.Future) -> None:
        """Callback executed when a subscriber task completes.

        Args:
            task_id: Unique identifier for the task.
            future: The completed task's future object.
        """
        tasks_done = self.running_tasks.pop(task_id)

        log.debug(f"Task '{tasks_done}' done")

    async def listen_topics(self) -> None:
        """Listen for and process incoming topic messages.

        This method runs continuously, receiving messages from registered topics
        and dispatching them to appropriate subscriber functions. Each subscriber
        is executed as a separate task.

        The method:
        1. Registers topics with the messaging backend
        2. Continuously waits for and processes messages
        3. Validates message format and content
        4. Dispatches messages to registered subscribers
        5. Manages task lifecycle and cleanup
        """
        # Mark ready as OK
        self.subscriber_ready.set()

        channel = await self.register_topics()

        while await self.wait_for_message(channel):
            raw = await self.get_next_message(channel)

            if hasattr(raw, "__iter__") and len(raw) != 2:
                log.error("Invalid data from Redis subscriber. It must be a " "tuple with len 2")

            ch, data = raw

            if hasattr(ch, "decode"):
                ch = ch.decode()

            # Get topic
            try:
                prefix, topic = ch.split(":", maxsplit=1)
            except ValueError:
                log.error(f"Invalid channel name: {ch}")
                continue

            # Check prefix
            if prefix != self.prefix:
                log.error(f"Invalid prefix: {prefix}")
                continue

            if hasattr(data, "encode"):
                data = data.encode()

            msg = msgpack.unpackb(data, raw=False)
            data_topic = msg.get("topic", False)
            data_content = msg.get("data", False)

            if not data_topic or not data_content:
                log.error(
                    f"Invalid data topic / data content - topic: {data_topic} / "
                    f"data: {data_content}"
                )
                continue

            for fn in self.topics_subscribers.get(topic, tuple()):
                # Build stop task
                task_id = uuid.uuid4().hex
                done_fn = partial(self._make_tasks_done_subscriber, task_id)

                task = asyncio.create_task(fn(data_topic, data_content))

                log.debug(f"Launching task '{fn.__name__}' for topic '{data_topic}'")

                task.add_done_callback(done_fn)

                self.running_tasks[task_id] = task

    @abc.abstractmethod
    def stop_subscriptions(self) -> None:  # pragma: no cover
        """Stop all active topic subscriptions.

        This method should clean up subscription resources and stop
        listening for new messages.
        """
        pass

    def build_subscribe_message(self, **kwargs: Any) -> bytes:
        """Build a message payload for publishing.

        Args:
            **kwargs: Key-value pairs to include in the message.

        Returns:
            Serialized message bytes using msgpack format.
        """
        return msgpack.packb(kwargs, use_bin_type=True)


class AsyncTaskDelayBase(metaclass=abc.ABCMeta):
    """Abstract base class for delayed task execution management.

    This class provides the foundation for implementing delayed/deferred task
    execution in asyncio applications. It manages task registration, queuing,
    concurrency control, retry logic, and execution.

    Attributes:
        task_prefix: Namespace prefix for tasks.
        task_running_tasks: Dictionary of currently running tasks.
        task_available_tasks: Dictionary of registered task functions.
        task_concurrency: Maximum number of concurrent task executions.
        task_list_name: Fully qualified name for the task queue.
        task_concurrency_sem: Semaphore controlling concurrent task execution.
        max_retries: Maximum number of retry attempts for failed tasks.
        task_ttl: Time-to-live for tasks in seconds.
    """

    # -------------------------------------------------------------------------
    # Implemented methods
    # -------------------------------------------------------------------------
    def __init__(
        self,
        prefix: str = "aiotasks",
        concurrency: int = 5,
        max_retries: int = 3,
        task_ttl: int = 3600,
    ) -> None:
        """Initialize the delayed task manager.

        Args:
            prefix: Namespace prefix for tasks. Defaults to "aiotasks".
            concurrency: Maximum number of concurrent task executions. Defaults to 5.
            max_retries: Maximum number of retry attempts for failed tasks. Defaults to 3.
            task_ttl: Time-to-live for tasks in seconds. Defaults to 3600 (1 hour).
        """
        self.task_prefix = prefix
        self.task_running_tasks: dict[str, asyncio.Task] = dict()
        self.task_available_tasks: dict[str, Callable] = dict()
        self.task_concurrency = concurrency
        self.task_list_name = "{}:{}".format(self.task_prefix, "tasks")
        self.max_retries = max_retries
        self.task_ttl = task_ttl

        # Semaphore for task_concurrency
        self.task_concurrency_sem = asyncio.BoundedSemaphore(self.task_concurrency)

    def task(self, name: str | None = None) -> Callable:
        """Decorator to register a coroutine function as a delayed task.

        Args:
            name: Optional custom name for the task. If None, uses function's __name__.

        Returns:
            Decorator function that registers the coroutine as a task and adds
            a .delay() method for deferred execution.

        Example:
            >>> @manager.task()
            >>> async def process_data(data):
            ...     await asyncio.sleep(1)
            ...     return data
            >>>
            >>> # Later, queue the task for execution
            >>> await process_data.delay({"key": "value"})
        """

        def real_decorator(f: Callable) -> Callable:
            # Real call to funcion
            def new_f(*args: Any, **kwargs: Any) -> Any:
                return f(*args, **kwargs)

            # if function is a coro, add some new functions
            if asyncio.iscoroutinefunction(f):
                if name:
                    function_name = name
                else:
                    function_name = f.__name__

                new_f.delay = partial(
                    self.context_class, new_f, self.task_list_name, self.poller, function_name
                )

                self.task_available_tasks[function_name] = f

            return new_f

        return real_decorator

    def add_task(self, function: Callable, name: str | None = None) -> Callable | None:
        """Programmatically add a coroutine function as a delayed task.

        Args:
            function: The coroutine function to register as a task.
            name: Optional custom name for the task. If None, uses function's __name__.

        Returns:
            The function object if successfully registered, None if function is not
            a coroutine.
        """
        if not asyncio.iscoroutinefunction(function):
            log.warning(
                f"Function '{function.__name__}' is not a coroutine and can't be added " "as a task"
            )
            return

        function.delay = partial(self.context_class, function, self.task_list_name, self.poller)

        if name:
            function_name = name
        else:
            function_name = function.__name__

        function.function_name = function_name

        self.task_available_tasks[function_name] = function

    def _make_tasks_done_delay(self, running_task: str, future: asyncio.Future) -> None:
        """Callback executed when a delayed task completes.

        Args:
            running_task: Unique identifier for the task.
            future: The completed task's future object.
        """
        self.task_running_tasks.pop(running_task)
        self.task_concurrency_sem.release()

        if hasattr(self, "custom_task_done"):
            self.custom_task_done(running_task)

    async def _function_runner(self, fn: Callable, task_id: str, *args: Any, **kwargs: Any) -> None:
        """Execute a task function with retry logic and error handling.

        Args:
            fn: The coroutine function to execute.
            task_id: Unique identifier for the task (for logging).
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        This method implements:
        - Exponential backoff retry logic
        - ACK on success (task completed successfully)
        - NACK on failure (task failed after all retries)
        - Comprehensive error logging
        """
        # Create a retry decorator dynamically based on max_retries
        retry_decorator = retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )

        # Wrap the function with retry logic
        retrying_fn = retry_decorator(fn)

        try:
            await retrying_fn(*args, **kwargs)
            # ACK - Task completed successfully
            log.info(f"Task {task_id} completed successfully")
            await self._task_ack(task_id)
        except RetryError as e:
            # NACK - Task failed after all retries
            log.error(
                f"Task {task_id} failed after {self.max_retries} attempts: {e.last_attempt.exception()}"
            )
            await self._task_nack(task_id, e.last_attempt.exception())
        except Exception as e:
            # NACK - Unexpected error
            log.error(f"Task {task_id} failed with unexpected error: {e}")
            await self._task_nack(task_id, e)

    async def _task_ack(self, task_id: str) -> None:
        """Acknowledge successful task completion.

        This method can be overridden by backends that support native ACK.

        Args:
            task_id: Unique identifier for the task.
        """
        # Default implementation - override in backends that support native ACK
        log.debug(f"ACK: Task {task_id}")

    async def _task_nack(self, task_id: str, error: Exception | None) -> None:
        """Negative acknowledge - task failed.

        This method can be overridden by backends that support native NACK.

        Args:
            task_id: Unique identifier for the task.
            error: The exception that caused the failure.
        """
        # Default implementation - override in backends that support native NACK
        log.debug(f"NACK: Task {task_id} - Error: {error}")

    async def listen_tasks(self) -> None:
        """Listen for and execute queued tasks.

        This method runs continuously, polling for pending tasks and executing
        them with concurrency control. Each task is:
        1. Retrieved from the pending queue
        2. Validated (UUID format, function existence)
        3. Executed with concurrency limits enforced by semaphore
        4. Tracked until completion
        """
        while True:
            raw_data = await self.pending_tasks

            # Limit concurrent executions
            await self.task_concurrency_sem.acquire()

            _, raw = raw_data

            msg = msgpack.unpackb(raw, raw=False)
            args = msg.get("args")
            kwargs = msg.get("kwargs")
            task_id = msg.get("task_id")
            task_function = msg.get("function")

            try:
                if type(task_id) is int:
                    task_id = str(task_id)

                uuid.UUID(task_id, version=4)
            except ValueError:
                log.error(f"Task ID '{task_id}' has not valid UUID4 format")
                continue

            try:
                local_task = self.task_available_tasks[task_function]
            except KeyError:
                log.warning(f"No local task with name '{task_function}'")
                continue

            running_task_id = uuid.uuid4().hex
            done_fn = partial(self._make_tasks_done_delay, running_task_id)

            # Build stop task
            task = asyncio.create_task(self._function_runner(local_task, task_id, *args, **kwargs))
            task.add_done_callback(done_fn)

            self.task_running_tasks[running_task_id] = task

    # -------------------------------------------------------------------------
    # Abstract methods & properties
    # -------------------------------------------------------------------------
    @abc.abstractmethod
    async def poller(self) -> Any:  # pragma: no cover
        """Poll for pending tasks from the queue backend.

        Returns:
            Task data from the queue.
        """
        pass

    @abc.abstractmethod
    async def has_pending_tasks(self) -> bool:  # pragma: no cover
        """Check if there are any pending tasks in the queue.

        Returns:
            True if there are pending tasks, False otherwise.
        """
        pass

    @abc.abstractmethod
    def stop_delayers(self) -> None:  # pragma: no cover
        """Stop the delayed task execution system.

        This method should clean up resources and stop polling for new tasks.
        """
        pass

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    @property
    @abc.abstractmethod
    def pending_tasks(self) -> Awaitable[Any]:  # pragma: no cover
        """Get the next pending task from the queue.

        Returns:
            Awaitable that resolves to the next pending task data.
        """
        pass

    @property
    @abc.abstractmethod
    def context_class(self) -> type:  # pragma: no cover
        """Get the context class for task execution.

        Returns:
            The class used to create task execution contexts.
        """
        pass


class AsyncTaskBase(metaclass=abc.ABCMeta):
    """Abstract base class combining task subscription and delayed execution.

    This class provides a unified interface for managing both publish/subscribe
    patterns and delayed task execution in asyncio applications.

    Attributes:
        dsn: Data Source Name for the messaging/queue backend.
        loop: The event loop to use for task execution.
    """

    def __init__(self, dsn: str, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Initialize the task manager.

        Args:
            dsn: Data Source Name (connection string) for the backend.
            loop: Optional event loop. If None, uses the current running loop
                 or creates a new one. Deprecated in Python 3.10+.
        """
        self.dsn = dsn
        self.loop = loop if loop is not None else asyncio.get_event_loop()

        # Set loop references for subclasses that need them
        # These are maintained for backward compatibility
        self._loop_subscribers = self.loop
        self._loop_delay = self.loop

        self._launcher_tasks: asyncio.Task | None = None
        self._launcher_topics: asyncio.Task | None = None

    async def wait(
        self, *, timeout: float = 0, exit_on_finish: bool = False, wait_timeout: float = 1.0
    ) -> None:
        """Wait for tasks to complete or timeout to expire.

        This method blocks asynchronously, checking for pending tasks and topics
        at regular intervals. It can exit on task completion or timeout.

        Args:
            timeout: Maximum time to wait in seconds. If 0, waits indefinitely.
                    Defaults to 0.
            exit_on_finish: If True, exits when all pending tasks are finished.
                          Defaults to False.
            wait_timeout: Polling interval in seconds. Defaults to 1.0.

        Example:
            >>> # Wait indefinitely until all tasks complete
            >>> await manager.wait(exit_on_finish=True)
            >>>
            >>> # Wait maximum 30 seconds
            >>> await manager.wait(timeout=30)
        """
        TIME_STEP = wait_timeout

        _infinite = False
        if timeout == 0:
            _infinite = True
        _start_time = time.time()

        while True:
            _has_pending_tasks = await self.has_pending_tasks()
            _has_pending_topics = await self.has_pending_topics()

            # There are pending tasks?
            if _has_pending_tasks or _has_pending_topics:
                # Yes, there's pending tasks, but is timeout reached?
                if time.time() - _start_time > timeout and not _infinite:
                    return
            else:
                # No tasks pending and marked ->
                #   -> If marked as a exit on tasks finished
                if exit_on_finish:
                    return

                # NO, there's not pending tasks, but is timeout reached?
                if time.time() - _start_time > timeout and not _infinite:
                    return

            # Wait
            await asyncio.sleep(TIME_STEP)

    def blocking_wait(
        self, *, timeout: float = 0, exit_on_finish: bool = False, wait_timeout: float = 1.0
    ) -> None:
        """Blocking version of wait() that runs in the event loop.

        This is a synchronous wrapper around wait() that blocks the current
        thread until the wait completes.

        Args:
            timeout: Maximum time to wait in seconds. If 0, waits indefinitely.
                    Defaults to 0.
            exit_on_finish: If True, exits when all pending tasks are finished.
                          Defaults to False.
            wait_timeout: Polling interval in seconds. Defaults to 1.0.

        Example:
            >>> # Blocking wait in synchronous code
            >>> manager.blocking_wait(timeout=30, exit_on_finish=True)
        """
        self.loop.run_until_complete(
            self.wait(timeout=timeout, exit_on_finish=exit_on_finish, wait_timeout=wait_timeout)
        )

    def stop(self) -> None:
        """Stop all task execution and clean up resources.

        This method:
        1. Stops delayed task polling
        2. Stops topic subscriptions
        3. Cancels all running tasks
        4. Stops event loops

        Warning:
            This is a destructive operation that will cancel all running tasks.
        """
        self.stop_delayers()
        self.stop_subscriptions()

        # Get all tasks for the subscriber and delay loops
        all_subscriber_tasks = asyncio.all_tasks(self._loop_subscribers)
        all_delay_tasks = asyncio.all_tasks(self._loop_delay)

        for t in all_subscriber_tasks:
            t.cancel()
        for t in all_delay_tasks:
            t.cancel()

        # Ensure all the tasks ends
        async def close_delay_loop() -> None:
            self._loop_delay.stop()

        async def close_subscribers_loop() -> None:
            self._loop_subscribers.stop()

        self.loop.run_until_complete(asyncio.ensure_future(close_delay_loop()))
        self.loop.run_until_complete(asyncio.ensure_future(close_subscribers_loop()))

    def run(self) -> None:
        """Start the task manager in blocking mode.

        This method launches both the topic listener and task listener,
        initiating the event processing loops. The method returns immediately
        after starting the tasks (non-blocking), but the listeners run
        continuously in the background.

        Note:
            Call blocking_wait() after run() to keep the program running
            until tasks complete.
        """
        self._launcher_topics = self._loop_subscribers.create_task(self.listen_topics())
        self._launcher_tasks = self._loop_delay.create_task(self.listen_tasks())


async def send_task(
    task_name: str,
    args: tuple | None = None,
    manager: AsyncTaskDelayBase | None = None,
    **kwargs: Any,
) -> Any:
    """Send a task for delayed execution.

    This function queues a task for execution by name, optionally using
    a specific manager or the current application's default manager.

    Args:
        task_name: Name of the registered task to execute.
        args: Positional arguments to pass to the task. Defaults to empty tuple.
        manager: Optional task manager to use. If None, uses current_app().
        **kwargs: Keyword arguments to pass to the task.

    Returns:
        The result from queuing the task.

    Raises:
        ValueError: If the task name doesn't exist in the manager.
        AssertionError: If manager is not an instance of AsyncTaskDelayBase.

    Example:
        >>> # Send a task using the current app manager
        >>> await send_task("process_data", args=(data,))
        >>>
        >>> # Send a task with a specific manager
        >>> await send_task("process_data", args=(data,), manager=my_manager)
    """
    if not manager:
        manager = current_app()

    assert isinstance(manager, AsyncTaskDelayBase)

    # Get function name
    try:
        fn_name = manager.task_available_tasks[task_name]
    except KeyError:
        raise ValueError("Function doesn't exist")

    if not args:
        args = tuple()

    # Get task
    task = partial(
        manager.context_class, fn_name, manager.task_list_name, manager.poller, task_name
    )

    return await task(*args, **kwargs)


def current_app() -> AsyncTaskDelayBase:
    """Get the current application's task manager.

    This function retrieves the global task manager instance stored in
    the builtins module.

    Returns:
        The current task manager instance.

    Raises:
        ValueError: If no task manager has been registered.

    Example:
        >>> manager = current_app()
        >>> await send_task("my_task", manager=manager)
    """
    import builtins

    # get the task manager
    manager = builtins.__aiotasks__

    if not manager:
        raise ValueError("Can't find aiotask manager")

    return manager


__all__ = (
    "AsyncTaskBase",
    "AsyncTaskDelayBase",
    "AsyncTaskSubscribeBase",
    "current_app",
    "send_task",
)
