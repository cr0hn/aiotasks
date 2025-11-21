"""AMQP/RabbitMQ backend implementation using aio-pika."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

import aio_pika
from aio_pika import Channel, Connection, ExchangeType, Message, Queue
from aio_pika.abc import AbstractIncomingMessage

from ..helpers import DSNConfig, parse_dsn
from .bases import AsyncTaskDelayBase, AsyncTaskSubscribeBase
from .context import AsyncWaitContextManager

log = logging.getLogger("aiotasks")


class AMQPAsyncWaitContextManager(AsyncWaitContextManager):
    """AMQP-specific context manager for task execution."""

    async def __await__(self) -> Any:
        """Submit task to AMQP queue."""
        message = Message(
            body=self.build_delay_message(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self.poller.default_exchange.publish(
            message,
            routing_key=self.list_name,
        )


class AsyncTaskSubscribeAMQP(AsyncTaskSubscribeBase):
    """AMQP pub/sub implementation for task subscribers using RabbitMQ."""

    def __init__(
        self,
        dsn: str = "amqp://guest:guest@localhost:5672/",
        prefix: str = "aiotasks",
        **kwargs: Any,
    ) -> None:
        """Initialize AMQP subscriber.

        Args:
            dsn: AMQP connection string (e.g., "amqp://user:pass@localhost:5672/vhost")
            prefix: Prefix for all exchanges and routing keys
            **kwargs: Additional arguments (loop is deprecated and ignored)
        """
        kwargs.pop("loop", None)
        super().__init__(prefix=prefix)

        self._dsn = dsn
        self._connection: Connection | None = None
        self._channel: Channel | None = None
        self._exchange: aio_pika.Exchange | None = None
        self._queue: Queue | None = None

    async def _ensure_connection(self) -> None:
        """Ensure AMQP connection is established."""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._dsn)
            self._channel = await self._connection.channel()

            # Declare exchange for pub/sub
            self._exchange = await self._channel.declare_exchange(
                f"{self.prefix}_pubsub",
                ExchangeType.TOPIC,
                durable=True,
            )

    async def publish(self, topic: str, info: Any) -> None:
        """Publish a message to a topic.

        Args:
            topic: The topic to publish to
            info: The data to publish
        """
        await self._ensure_connection()

        if not self.subscriber_ready.is_set():
            await self.subscriber_ready.wait()

        message_body = self.build_subscribe_message(topic=topic, data=info)
        message = Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        routing_key = f"{self.prefix}.{topic}"
        if self._exchange:
            await self._exchange.publish(message, routing_key=routing_key)
            log.debug("Published message to topic: %s", topic)

    async def has_pending_topics(self) -> bool:
        """Check if there are pending topic handlers running.

        Returns:
            True if there are running tasks, False otherwise
        """
        return bool(self.running_tasks)

    async def register_topics(self) -> Queue:
        """Register subscriptions for all topics.

        Returns:
            Queue object for message listening
        """
        await self._ensure_connection()

        if self._channel:
            # Create exclusive queue for this subscriber
            self._queue = await self._channel.declare_queue("", exclusive=True)

            # Bind to all topics (pattern matching with #)
            if self._exchange and self._queue:
                await self._queue.bind(
                    self._exchange,
                    routing_key=f"{self.prefix}.#",
                )
                log.debug("Subscribed to pattern: %s.#", self.prefix)

        return self._queue  # type: ignore[return-value]

    async def wait_for_message(self, _channel: Queue) -> bool:
        """Wait for a message on the channel.

        Args:
            _channel: Queue object to wait on (unused, kept for API compat)

        Returns:
            True if should continue listening, False otherwise
        """
        return True

    async def get_next_message(self, channel: Queue) -> tuple[bytes, bytes]:
        """Get the next message from the queue.

        Args:
            channel: Queue object to get message from

        Returns:
            Tuple of (routing_key, data)
        """
        async with channel.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    # Extract topic from routing key
                    routing_key = message.routing_key or ""
                    return routing_key.encode(), message.body

        # Should not reach here
        await asyncio.sleep(0.1)
        return b"", b""

    def stop_subscriptions(self) -> None:
        """Stop all subscriptions and close connections."""
        if self._connection:
            _ = asyncio.create_task(self._connection.close())
        log.debug("AMQP subscriptions stopped")


class AsyncTaskDelayAMQP(AsyncTaskDelayBase):
    """AMQP implementation for delayed task execution using RabbitMQ."""

    def __init__(
        self,
        dsn: str = "amqp://guest:guest@localhost:5672/",
        prefix: str = "aiotasks",
        concurrency: int = 5,
        **kwargs: Any,
    ) -> None:
        """Initialize AMQP delay backend.

        Args:
            dsn: AMQP connection string
            prefix: Prefix for all queues
            concurrency: Maximum number of concurrent tasks
            **kwargs: Additional arguments (loop is deprecated and ignored)
        """
        kwargs.pop("loop", None)
        super().__init__(prefix=prefix, concurrency=concurrency)

        self._dsn = dsn
        self._connection: Connection | None = None
        self._channel: Channel | None = None
        self._queue: Queue | None = None

    async def _ensure_connection(self) -> None:
        """Ensure AMQP connection is established."""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._dsn)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=self.task_concurrency)

            # Declare task queue
            self._queue = await self._channel.declare_queue(
                self.task_list_name,
                durable=True,
            )

    async def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks.

        Returns:
            True if there are running or queued tasks, False otherwise
        """
        # For AMQP, we check running tasks
        # Queue message count would require additional API call
        return bool(self.task_running_tasks)

    def stop_delayers(self) -> None:
        """Stop the delay backend and cancel running tasks."""
        for task in self.task_running_tasks.values():
            task.cancel()

        if self._connection:
            _ = asyncio.create_task(self._connection.close())

        log.debug("AMQP delayers stopped")

    @property
    def poller(self) -> Channel:
        """Get the AMQP channel for task submission.

        Returns:
            AMQP channel
        """
        return self._channel  # type: ignore[return-value]

    @property
    def context_class(self) -> type[AMQPAsyncWaitContextManager]:
        """Get the context manager class for this backend.

        Returns:
            AMQPAsyncWaitContextManager class
        """
        return AMQPAsyncWaitContextManager

    @property
    def pending_tasks(self) -> AsyncGenerator[tuple[str, bytes], None]:
        """Get an async generator of pending tasks.

        Yields:
            Tuple of (queue_name, task_data)
        """
        return self._pending_tasks_generator()

    async def _pending_tasks_generator(self) -> AsyncGenerator[tuple[str, bytes], None]:
        """Generator that yields pending tasks from AMQP.

        Yields:
            Tuple of (queue_name, task_data)
        """
        await self._ensure_connection()

        if self._queue:
            async with self._queue.iterator() as queue_iter:
                message: AbstractIncomingMessage
                async for message in queue_iter:
                    async with message.process():
                        yield self.task_list_name, message.body


__all__ = ("AsyncTaskSubscribeAMQP", "AsyncTaskDelayAMQP")
