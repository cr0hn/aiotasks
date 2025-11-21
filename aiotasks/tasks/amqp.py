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

from .bases import AsyncTaskDelayBase, AsyncTaskSubscribeBase
from .context import AsyncWaitContextManager

log = logging.getLogger("aiotasks")


class AMQPAsyncWaitContextManager(AsyncWaitContextManager):
    """AMQP-specific context manager for task execution."""

    async def __await__(self) -> Any:
        """Submit task to AMQP queue with TTL.

        Uses default exchange to send directly to queue.
        This ensures only ONE worker processes each task.
        """
        # Get TTL from the backend if available
        ttl_ms = None
        if hasattr(self.poller, "task_ttl"):
            ttl_ms = self.poller.task_ttl * 1000  # Convert to milliseconds

        message = Message(
            body=self.build_delay_message(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            expiration=ttl_ms,  # TTL in milliseconds
        )
        # Use default exchange to route directly to queue
        # This is CRITICAL: ensures only one consumer gets the message
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

            # Declare Topic exchange for pub/sub
            # IMPORTANT: This is for .subscribe() not for .delay()
            # All subscribers receive messages (fanout pattern)
            self._exchange = await self._channel.declare_exchange(
                f"{self.prefix}_pubsub",
                ExchangeType.TOPIC,
                durable=True,
            )

    async def publish(self, topic: str, info: Any) -> None:
        """Publish a message to a topic using pub/sub pattern.

        This uses Topic Exchange so ALL subscribers receive the message.
        This is different from .delay() which uses a queue (only one worker).

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
            # Publish to exchange - ALL bound queues receive it
            await self._exchange.publish(message, routing_key=routing_key)
            log.debug("Published message to topic: %s", topic)

    async def has_pending_topics(self) -> bool:
        """Check if there are pending topic handlers running.

        Returns:
            True if there are running tasks, False otherwise
        """
        return bool(self.running_tasks)

    async def register_topics(self) -> Queue:
        """Register subscriptions for all topics using pub/sub pattern.

        Creates an EXCLUSIVE queue for this subscriber.
        Each subscriber gets its own queue bound to the exchange.
        This ensures ALL subscribers receive every message.

        Returns:
            Queue object for message listening
        """
        await self._ensure_connection()

        if self._channel:
            # Create EXCLUSIVE queue for THIS subscriber only
            # Each subscriber gets their own queue - this is KEY for pub/sub
            self._queue = await self._channel.declare_queue("", exclusive=True)

            # Bind to all topics (pattern matching with #)
            if self._exchange and self._queue:
                await self._queue.bind(
                    self._exchange,
                    routing_key=f"{self.prefix}.#",
                )
                log.debug(
                    "Subscribed to pattern: %s.# (exclusive queue for this subscriber)", self.prefix
                )

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
        max_retries: int = 3,
        task_ttl: int = 3600,
        **kwargs: Any,
    ) -> None:
        """Initialize AMQP delay backend.

        Args:
            dsn: AMQP connection string
            prefix: Prefix for all queues
            concurrency: Maximum number of concurrent tasks
            max_retries: Maximum number of retry attempts for failed tasks
            task_ttl: Time-to-live for tasks in seconds
            **kwargs: Additional arguments (loop is deprecated and ignored)
        """
        kwargs.pop("loop", None)
        super().__init__(
            prefix=prefix,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
        )

        self._dsn = dsn
        self._connection: Connection | None = None
        self._channel: Channel | None = None
        self._queue: Queue | None = None
        # Track messages for ACK/NACK
        self._current_messages: dict[str, AbstractIncomingMessage] = {}

    async def _ensure_connection(self) -> None:
        """Ensure AMQP connection is established."""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._dsn)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=self.task_concurrency)

            # Declare SHARED task queue
            # IMPORTANT: This is a NAMED queue (not exclusive)
            # Multiple workers can consume from it, but each message
            # goes to ONLY ONE worker (round-robin distribution)
            self._queue = await self._channel.declare_queue(
                self.task_list_name,
                durable=True,
                exclusive=False,  # Explicitly not exclusive - shared among workers
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

        Stores messages for later ACK/NACK instead of auto-acknowledging.

        Yields:
            Tuple of (queue_name, task_data)
        """
        await self._ensure_connection()

        if self._queue:
            async with self._queue.iterator() as queue_iter:
                message: AbstractIncomingMessage
                async for message in queue_iter:
                    # Do NOT use message.process() - we'll manually ACK/NACK
                    # Extract task_id to store message for later ACK/NACK
                    try:
                        msg = msgpack.unpackb(message.body, raw=False)
                        task_id = msg.get("task_id")
                        if task_id:
                            # Store message for later ACK/NACK
                            self._current_messages[str(task_id)] = message
                    except Exception as e:
                        log.error("Failed to extract task_id from message: %s", e)
                        # Reject message since we can't process it
                        await message.reject(requeue=False)
                        continue

                    yield self.task_list_name, message.body

    async def _task_ack(self, task_id: str) -> None:
        """Acknowledge successful task completion in AMQP.

        Uses native AMQP acknowledgment.

        Args:
            task_id: Unique identifier for the task.
        """
        await super()._task_ack(task_id)

        # ACK the AMQP message
        message = self._current_messages.pop(task_id, None)
        if message:
            await message.ack()
            log.debug("AMQP ACK: Task %s", task_id)
        else:
            log.warning("No AMQP message found for task %s (cannot ACK)", task_id)

    async def _task_nack(self, task_id: str, error: Exception | None) -> None:
        """Negative acknowledge - task failed in AMQP.

        Uses native AMQP rejection (no requeue).

        Args:
            task_id: Unique identifier for the task.
            error: The exception that caused the failure.
        """
        await super()._task_nack(task_id, error)

        # NACK (reject) the AMQP message without requeue
        message = self._current_messages.pop(task_id, None)
        if message:
            await message.reject(requeue=False)
            log.debug("AMQP NACK: Task %s - Error: %s", task_id, error)
        else:
            log.warning("No AMQP message found for task %s (cannot NACK)", task_id)

    async def cleanup_old_tasks(self) -> int:
        """Clean up old unacknowledged messages.

        AMQP handles message expiration via TTL, but this can clean up
        orphaned message references in our tracking dict.

        Returns:
            Number of messages cleaned up.
        """
        # Clean up any messages that are still in _current_messages
        # but might be orphaned
        cleaned = len(self._current_messages)
        self._current_messages.clear()
        log.debug("Cleaned up %d orphaned message references", cleaned)
        return cleaned


__all__ = ("AsyncTaskDelayAMQP", "AsyncTaskSubscribeAMQP")
