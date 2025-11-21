"""Redis backend implementation using redis.asyncio for Redis >=6."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from typing import Any

with contextlib.suppress(ImportError):
    import umsgpack as msgpack  # noqa: F401

import msgpack  # type: ignore[import-not-found]
from redis import asyncio as aioredis
from redis.asyncio.client import PubSub, Redis

from ..helpers import DSNConfig, parse_dsn
from .bases import AsyncTaskDelayBase, AsyncTaskSubscribeBase
from .context import AsyncWaitContextManager

log = logging.getLogger("aiotasks")


class RedisAsyncWaitContextManager(AsyncWaitContextManager):
    """Redis-specific context manager for task execution."""

    def __await__(self) -> Any:
        """Submit task to Redis queue."""
        return self.poller.lpush(
            self.list_name,
            self.build_delay_message(),
        ).__await__()


class AsyncTaskSubscribeRedis(AsyncTaskSubscribeBase):
    """Redis pub/sub implementation for task subscribers."""

    def __init__(
        self,
        dsn: str = "redis://127.0.0.1:6379/0",
        prefix: str = "aiotasks",
        **kwargs: Any,
    ) -> None:
        """Initialize Redis subscriber.

        Args:
            dsn: Redis connection string
            prefix: Prefix for all Redis keys/channels
            **kwargs: Additional arguments (loop is deprecated and ignored)
        """
        # Remove deprecated loop argument if present
        kwargs.pop("loop", None)

        super().__init__(prefix=prefix)

        config: DSNConfig = parse_dsn(dsn, default_port=6379, default_db=0)

        # Create Redis clients for pub/sub
        self._redis_pub: Redis = aioredis.Redis(
            host=config.host,
            port=config.port,
            db=int(config.db) if isinstance(config.db, str) else config.db,
            password=config.password,
            decode_responses=False,  # We handle encoding manually
        )

        self._redis_sub: Redis = aioredis.Redis(
            host=config.host,
            port=config.port,
            db=int(config.db) if isinstance(config.db, str) else config.db,
            password=config.password,
            decode_responses=False,
        )

        self._pubsub: PubSub | None = None

    async def publish(self, topic: str, info: Any) -> None:
        """Publish a message to a topic.

        Args:
            topic: The topic/channel to publish to
            info: The data to publish
        """
        # Wait for subscriber to be ready
        if not self.subscriber_ready.is_set():
            await self.subscriber_ready.wait()

        channel = f"{self.prefix}:{topic}"
        message = self.build_subscribe_message(topic=topic, data=info)

        await self._redis_pub.publish(channel, message)
        log.debug("Published message to channel: %s", channel)

    async def has_pending_topics(self) -> bool:
        """Check if there are pending topic handlers running.

        Returns:
            True if there are running tasks, False otherwise
        """
        return bool(self.running_tasks)

    async def register_topics(self) -> PubSub:
        """Register pattern subscription for all topics.

        Returns:
            PubSub object for message listening
        """
        self._pubsub = self._redis_sub.pubsub()
        pattern = f"{self.prefix}:*"
        await self._pubsub.psubscribe(pattern)
        log.debug("Subscribed to pattern: %s", pattern)
        return self._pubsub

    async def wait_for_message(self, _channel: PubSub) -> bool:
        """Wait for a message on the channel.

        Args:
            _channel: PubSub object to wait on (unused, kept for API compat)

        Returns:
            True if should continue listening, False otherwise
        """
        # redis.asyncio doesn't have wait_message, we iterate
        return True

    async def get_next_message(self, channel: PubSub) -> tuple[bytes, bytes]:
        """Get the next message from the channel.

        Args:
            channel: PubSub object to get message from

        Returns:
            Tuple of (channel, data)
        """
        while True:
            message = await channel.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message["type"] == "pmessage":
                return message["channel"], message["data"]
            # If no message, sleep briefly to avoid busy loop
            await asyncio.sleep(0.01)

    def stop_subscriptions(self) -> None:
        """Stop all subscriptions and close connections."""
        if self._pubsub:
            _ = asyncio.create_task(self._pubsub.close())

        _ = asyncio.create_task(self._redis_sub.close())
        _ = asyncio.create_task(self._redis_pub.close())

        log.debug("Redis subscriptions stopped")


class AsyncTaskDelayRedis(AsyncTaskDelayBase):
    """Redis implementation for delayed task execution."""

    def __init__(
        self,
        dsn: str = "redis://127.0.0.1:6379/0",
        prefix: str = "aiotasks",
        concurrency: int = 5,
        **kwargs: Any,
    ) -> None:
        """Initialize Redis delay backend.

        Args:
            dsn: Redis connection string
            prefix: Prefix for all Redis keys
            concurrency: Maximum number of concurrent tasks
            **kwargs: Additional arguments (loop is deprecated and ignored)
        """
        # Remove deprecated loop argument if present
        kwargs.pop("loop", None)

        super().__init__(prefix=prefix, concurrency=concurrency)

        config: DSNConfig = parse_dsn(dsn, default_port=6379, default_db=0)

        # Create Redis clients
        self._redis_consumer: Redis = aioredis.Redis(
            host=config.host,
            port=config.port,
            db=int(config.db) if isinstance(config.db, str) else config.db,
            password=config.password,
            decode_responses=False,
        )

        self._redis_poller: Redis = aioredis.Redis(
            host=config.host,
            port=config.port,
            db=int(config.db) if isinstance(config.db, str) else config.db,
            password=config.password,
            decode_responses=False,
        )

    async def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks.

        Returns:
            True if there are running or queued tasks, False otherwise
        """
        queue_length = await self._redis_poller.llen(self.task_list_name)
        return bool(self.task_running_tasks) or queue_length > 0

    def stop_delayers(self) -> None:
        """Stop the delay backend and cancel running tasks."""
        # Cancel all running tasks
        for task in self.task_running_tasks.values():
            task.cancel()

        # Close Redis connections
        _ = asyncio.create_task(self._redis_consumer.close())
        _ = asyncio.create_task(self._redis_poller.close())

        log.debug("Redis delayers stopped")

    @property
    def poller(self) -> Redis:
        """Get the poller Redis client.

        Returns:
            Redis client for task submission
        """
        return self._redis_poller

    @property
    def context_class(self) -> type[RedisAsyncWaitContextManager]:
        """Get the context manager class for this backend.

        Returns:
            RedisAsyncWaitContextManager class
        """
        return RedisAsyncWaitContextManager

    @property
    def pending_tasks(self) -> AsyncGenerator[tuple[str, bytes], None]:
        """Get an async generator of pending tasks.

        Yields:
            Tuple of (queue_name, task_data)
        """
        return self._pending_tasks_generator()

    async def _pending_tasks_generator(self) -> AsyncGenerator[tuple[str, bytes], None]:
        """Generator that yields pending tasks from Redis.

        Yields:
            Tuple of (queue_name, task_data)
        """
        while True:
            # BRPOP returns (key, value) or None
            result = await self._redis_consumer.brpop(self.task_list_name, timeout=1)
            if result:
                yield result
            else:
                # Yield control back to allow cancellation
                await asyncio.sleep(0.01)


__all__ = ("AsyncTaskSubscribeRedis", "AsyncTaskDelayRedis")
