import asyncio
import logging

from .bases import *
from .context import AsyncWaitContextManager

log = logging.getLogger("aiotasks")


class MemoryAsyncWaitContextManager(AsyncWaitContextManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __await__(self, *args, **kwargs):
        return asyncio.ensure_future(
            self.poller.put((self.list_name,
                             self.build_delay_message())),
            loop=self.loop).__await__()


class AsyncTaskSubscribeMemory(AsyncTaskSubscribeBase):
    """Memory pub/sub implementation.

    Uses separate queues for each subscriber to implement true pub/sub.
    Each subscriber gets ALL published messages (broadcast pattern).
    """

    def __init__(self,
                 prefix: str = "aiotasks",
                 loop=None):
        super().__init__(loop=loop, prefix=prefix)

        self._loop_subscribers = loop or asyncio.get_event_loop()
        # Each subscriber gets its own queue for true pub/sub
        self._subscriber_queues: list[asyncio.Queue] = []

    async def publish(self, topic, info):
        """Publish message to ALL subscribers (true pub/sub).

        Each subscriber has their own queue and receives a copy of the message.
        This is different from .delay() which uses ONE shared queue.
        """
        message = (
            "{}:{}".format(self.prefix, topic),
            self.build_subscribe_message(**dict(topic=topic, data=info))
        )

        # Put message in ALL subscriber queues (broadcast)
        for queue in self._subscriber_queues:
            await queue.put(message)

    async def has_pending_topics(self):
        """Check if any subscriber queues have pending messages."""
        return any(not q.empty() for q in self._subscriber_queues)

    async def register_topics(self):
        """Register a new subscriber with its own queue.

        Returns a new queue for this subscriber.
        Each subscriber independently receives all messages.
        """
        # Create a new queue for this subscriber
        new_queue = asyncio.Queue(loop=self._loop_subscribers)
        self._subscriber_queues.append(new_queue)
        return new_queue

    async def wait_for_message(self, channel):
        return True

    async def get_next_message(self, channel):
        """Get next message from this subscriber's queue."""
        return await channel.get()

    def stop_subscriptions(self):
        for t in self.running_tasks.values():
            t.cancel()
        self._subscriber_queues.clear()


# -------------------------------------------------------------------------
# Delayers
# -------------------------------------------------------------------------
class AsyncTaskDelayMemory(AsyncTaskDelayBase):
    """Memory backend for task queuing.

    Uses a single shared asyncio.Queue which ensures only ONE worker
    processes each task (FIFO queue pattern, not pub/sub).
    """

    def __init__(self,
                 dsn=None,
                 prefix: str = "aiotasks",
                 loop=None,
                 concurrency: int = 5):
        super().__init__(loop=loop, prefix=prefix, concurrency=concurrency)

        # Single shared queue - tasks are distributed round-robin to workers
        # Only ONE worker gets each task (correct queue behavior)
        self._task_queue = asyncio.Queue(loop=self._loop_delay)

    async def has_pending_tasks(self):
        """Check if there are pending or running tasks."""
        return not self._task_queue.empty() or bool(self.task_running_tasks)

    def custom_task_done(self, task_id):
        """Mark task as done in queue."""
        self._task_queue.task_done()

    def stop_delayers(self):
        """Stop all running tasks."""
        for t in self.task_running_tasks.values():
            t.cancel()

    @property
    def pending_tasks(self):
        """Get next task from queue.

        Only ONE worker will receive this task (queue pattern).
        This is correct behavior for task distribution.
        """
        return self._task_queue.get()

    @property
    def context_class(self):
        return MemoryAsyncWaitContextManager

    @property
    def poller(self):
        """Get the task queue for task submission."""
        return self._task_queue


__all__ = ("AsyncTaskSubscribeMemory", "AsyncTaskDelayMemory")
