"""ZeroMQ backend implementation using pyzmq.

ZeroMQ Pattern Usage:
- Tasks (.delay()): PUSH/PULL pattern - load balanced, only ONE worker gets each task
- Subscriptions (.subscribe()): PUB/SUB pattern - ALL subscribers receive messages
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

import zmq
import zmq.asyncio

from ..helpers import DSNConfig, parse_dsn
from .bases import AsyncTaskDelayBase, AsyncTaskSubscribeBase
from .context import AsyncWaitContextManager

log = logging.getLogger("aiotasks")


class ZMQAsyncWaitContextManager(AsyncWaitContextManager):
    """ZeroMQ-specific context manager for task execution."""

    async def __await__(self) -> Any:
        """Submit task to ZeroMQ PUSH socket.

        Uses PUSH/PULL pattern for load balancing.
        Each task goes to ONE worker only (round-robin).
        """
        message = self.build_delay_message()
        await self.poller.send(message)


class AsyncTaskSubscribeZMQ(AsyncTaskSubscribeBase):
    """ZeroMQ pub/sub implementation for task subscribers.

    Uses PUB/SUB pattern where ALL subscribers receive each message.
    Each subscriber connects to the publisher and receives a copy.
    """

    def __init__(
        self,
        dsn: str = "zmq://127.0.0.1:5555",
        prefix: str = "aiotasks",
        **kwargs: Any,
    ) -> None:
        """Initialize ZeroMQ subscriber.

        Args:
            dsn: ZeroMQ connection string (e.g., "zmq://localhost:5555")
            prefix: Prefix for all topics
            **kwargs: Additional arguments (loop is deprecated and ignored)
        """
        kwargs.pop("loop", None)
        super().__init__(prefix=prefix)

        config: DSNConfig = parse_dsn(dsn, default_port=5555)

        # Create ZeroMQ context and sockets
        self._zmq_context = zmq.asyncio.Context()

        # Publisher socket (PUB) - ONE publisher
        self._pub_socket: zmq.asyncio.Socket = self._zmq_context.socket(zmq.PUB)
        pub_endpoint = f"tcp://{config.host}:{config.port}"
        self._pub_socket.bind(pub_endpoint)
        log.debug("ZMQ PUB socket bound to: %s", pub_endpoint)

        # Subscriber socket (SUB) - connects to publisher
        # Each subscriber process will have its own SUB socket
        self._sub_socket: zmq.asyncio.Socket = self._zmq_context.socket(zmq.SUB)
        # SUB connects to PUB (not bind)
        self._sub_socket.connect(pub_endpoint)
        log.debug("ZMQ SUB socket connected to: %s", pub_endpoint)

    async def publish(self, topic: str, info: Any) -> None:
        """Publish a message to a topic using PUB/SUB pattern.

        All subscribers with matching topic filter will receive this message.
        This is true broadcast - every subscriber gets a copy.

        Args:
            topic: The topic to publish to
            info: The data to publish
        """
        if not self.subscriber_ready.is_set():
            await self.subscriber_ready.wait()

        full_topic = f"{self.prefix}:{topic}"
        message_body = self.build_subscribe_message(topic=topic, data=info)

        # ZMQ pub/sub uses multipart messages: [topic, data]
        # ALL subscribers with matching filter receive this
        await self._pub_socket.send_multipart([
            full_topic.encode(),
            message_body,
        ])
        log.debug("Published to all subscribers on topic: %s", topic)

    async def has_pending_topics(self) -> bool:
        """Check if there are pending topic handlers running.

        Returns:
            True if there are running tasks, False otherwise
        """
        return bool(self.running_tasks)

    async def register_topics(self) -> zmq.asyncio.Socket:
        """Register subscriptions for all topics.

        Subscribes to topic pattern. Each subscriber independently
        receives all matching messages (true pub/sub).

        Returns:
            Socket object for message listening
        """
        # Subscribe to all topics with our prefix
        # Each subscriber that does this will receive ALL matching messages
        subscription_filter = f"{self.prefix}:".encode()
        self._sub_socket.setsockopt(zmq.SUBSCRIBE, subscription_filter)
        log.debug("Subscribed to pattern: %s* (will receive all matching messages)", self.prefix)
        return self._sub_socket

    async def wait_for_message(self, _channel: zmq.asyncio.Socket) -> bool:
        """Wait for a message on the channel.

        Args:
            _channel: Socket to wait on (unused, kept for API compat)

        Returns:
            True if should continue listening, False otherwise
        """
        return True

    async def get_next_message(self, channel: zmq.asyncio.Socket) -> tuple[bytes, bytes]:
        """Get the next message from the socket.

        Args:
            channel: Socket to get message from

        Returns:
            Tuple of (topic, data)
        """
        # ZMQ pub/sub messages are multipart: [topic, data]
        parts = await channel.recv_multipart()
        if len(parts) >= 2:
            return parts[0], parts[1]

        # Fallback
        return b"", b""

    def stop_subscriptions(self) -> None:
        """Stop all subscriptions and close connections."""
        self._pub_socket.close()
        self._sub_socket.close()
        self._zmq_context.term()
        log.debug("ZMQ subscriptions stopped")


class AsyncTaskDelayZMQ(AsyncTaskDelayBase):
    """ZeroMQ implementation for delayed task execution.

    Uses PUSH/PULL pattern for load-balanced task distribution.
    Each task goes to exactly ONE worker (round-robin by ZeroMQ).
    """

    def __init__(
        self,
        dsn: str = "zmq://127.0.0.1:5556",
        prefix: str = "aiotasks",
        concurrency: int = 5,
        **kwargs: Any,
    ) -> None:
        """Initialize ZeroMQ delay backend with PUSH/PULL pattern.

        Args:
            dsn: ZeroMQ connection string
            prefix: Prefix for all queues
            concurrency: Maximum number of concurrent tasks
            **kwargs: Additional arguments (loop is deprecated and ignored)
        """
        kwargs.pop("loop", None)
        super().__init__(prefix=prefix, concurrency=concurrency)

        config: DSNConfig = parse_dsn(dsn, default_port=5556)

        # Create ZeroMQ context and sockets
        self._zmq_context = zmq.asyncio.Context()

        # PUSH socket for sending tasks (ventilator pattern)
        # This BINDS - clients will connect to push tasks
        self._push_socket: zmq.asyncio.Socket = self._zmq_context.socket(zmq.PUSH)
        push_endpoint = f"tcp://{config.host}:{config.port}"
        self._push_socket.bind(push_endpoint)
        log.debug("ZMQ PUSH socket bound to: %s (for task submission)", push_endpoint)

        # PULL socket for receiving tasks (worker pattern)
        # This CONNECTS to where tasks are pushed
        # Multiple workers can connect - ZeroMQ distributes tasks round-robin
        self._pull_socket: zmq.asyncio.Socket = self._zmq_context.socket(zmq.PULL)
        # Workers connect to the same push endpoint
        self._pull_socket.connect(push_endpoint)
        log.debug("ZMQ PULL socket connected to: %s (will receive tasks round-robin)", push_endpoint)

    async def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks.

        Returns:
            True if there are running tasks, False otherwise

        Note:
            ZMQ PUSH/PULL doesn't expose queue depth, so we only
            check running tasks. Messages in flight are unknown.
        """
        return bool(self.task_running_tasks)

    def stop_delayers(self) -> None:
        """Stop the delay backend and cancel running tasks."""
        for task in self.task_running_tasks.values():
            task.cancel()

        self._push_socket.close()
        self._pull_socket.close()
        self._zmq_context.term()
        log.debug("ZMQ delayers stopped")

    @property
    def poller(self) -> zmq.asyncio.Socket:
        """Get the ZMQ socket for task submission.

        Returns:
            ZMQ PUSH socket (tasks are load-balanced to PULL workers)
        """
        return self._push_socket

    @property
    def context_class(self) -> type[ZMQAsyncWaitContextManager]:
        """Get the context manager class for this backend.

        Returns:
            ZMQAsyncWaitContextManager class
        """
        return ZMQAsyncWaitContextManager

    @property
    def pending_tasks(self) -> AsyncGenerator[tuple[str, bytes], None]:
        """Get an async generator of pending tasks.

        Yields:
            Tuple of (queue_name, task_data)
        """
        return self._pending_tasks_generator()

    async def _pending_tasks_generator(self) -> AsyncGenerator[tuple[str, bytes], None]:
        """Generator that yields pending tasks from ZeroMQ PULL socket.

        Uses PULL pattern - each task is received by exactly ONE worker.
        ZeroMQ handles round-robin distribution automatically.

        Yields:
            Tuple of (queue_name, task_data)
        """
        while True:
            try:
                # Receive with timeout to allow for cancellation
                # PULL ensures only THIS worker gets each message (no duplicates)
                message = await asyncio.wait_for(
                    self._pull_socket.recv(),
                    timeout=1.0,
                )
                yield self.task_list_name, message
            except TimeoutError:
                # No message, yield control
                await asyncio.sleep(0.01)


__all__ = ("AsyncTaskSubscribeZMQ", "AsyncTaskDelayZMQ")
