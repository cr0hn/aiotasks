"""ZeroMQ backend implementation using pyzmq."""

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
        """Submit task to ZeroMQ socket."""
        message = self.build_delay_message()
        await self.poller.send(message)


class AsyncTaskSubscribeZMQ(AsyncTaskSubscribeBase):
    """ZeroMQ pub/sub implementation for task subscribers."""

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

        # Publisher socket (PUB)
        self._pub_socket: zmq.asyncio.Socket = self._zmq_context.socket(zmq.PUB)
        pub_endpoint = f"tcp://{config.host}:{config.port}"
        self._pub_socket.bind(pub_endpoint)
        log.debug("ZMQ publisher bound to: %s", pub_endpoint)

        # Subscriber socket (SUB)
        self._sub_socket: zmq.asyncio.Socket = self._zmq_context.socket(zmq.SUB)
        sub_endpoint = f"tcp://{config.host}:{config.port + 1}"
        self._sub_socket.bind(sub_endpoint)
        log.debug("ZMQ subscriber bound to: %s", sub_endpoint)

    async def publish(self, topic: str, info: Any) -> None:
        """Publish a message to a topic.

        Args:
            topic: The topic to publish to
            info: The data to publish
        """
        if not self.subscriber_ready.is_set():
            await self.subscriber_ready.wait()

        full_topic = f"{self.prefix}:{topic}"
        message_body = self.build_subscribe_message(topic=topic, data=info)

        # ZMQ pub/sub uses multipart messages: [topic, data]
        await self._pub_socket.send_multipart([
            full_topic.encode(),
            message_body,
        ])
        log.debug("Published message to topic: %s", topic)

    async def has_pending_topics(self) -> bool:
        """Check if there are pending topic handlers running.

        Returns:
            True if there are running tasks, False otherwise
        """
        return bool(self.running_tasks)

    async def register_topics(self) -> zmq.asyncio.Socket:
        """Register subscriptions for all topics.

        Returns:
            Socket object for message listening
        """
        # Subscribe to all topics with our prefix
        subscription_filter = f"{self.prefix}:".encode()
        self._sub_socket.setsockopt(zmq.SUBSCRIBE, subscription_filter)
        log.debug("Subscribed to pattern: %s*", self.prefix)
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
    """ZeroMQ implementation for delayed task execution."""

    def __init__(
        self,
        dsn: str = "zmq://127.0.0.1:5556",
        prefix: str = "aiotasks",
        concurrency: int = 5,
        **kwargs: Any,
    ) -> None:
        """Initialize ZeroMQ delay backend.

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

        # PUSH socket for sending tasks
        self._push_socket: zmq.asyncio.Socket = self._zmq_context.socket(zmq.PUSH)
        push_endpoint = f"tcp://{config.host}:{config.port}"
        self._push_socket.bind(push_endpoint)
        log.debug("ZMQ pusher bound to: %s", push_endpoint)

        # PULL socket for receiving tasks
        self._pull_socket: zmq.asyncio.Socket = self._zmq_context.socket(zmq.PULL)
        pull_endpoint = f"tcp://{config.host}:{config.port + 1}"
        self._pull_socket.bind(pull_endpoint)
        log.debug("ZMQ puller bound to: %s", pull_endpoint)

    async def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks.

        Returns:
            True if there are running tasks, False otherwise
        """
        # ZMQ doesn't provide easy queue length access
        # We only check running tasks
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
            ZMQ PUSH socket
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
        """Generator that yields pending tasks from ZeroMQ.

        Yields:
            Tuple of (queue_name, task_data)
        """
        while True:
            try:
                # Receive with timeout to allow for cancellation
                message = await asyncio.wait_for(
                    self._pull_socket.recv(),
                    timeout=1.0,
                )
                yield self.task_list_name, message
            except TimeoutError:
                # No message, yield control
                await asyncio.sleep(0.01)


__all__ = ("AsyncTaskSubscribeZMQ", "AsyncTaskDelayZMQ")
