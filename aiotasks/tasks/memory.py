import asyncio
import logging

from .bases import *
from .context import AsyncWaitContextManager

log = logging.getLogger("aiotasks")


class MemoryAsyncWaitContextManager(AsyncWaitContextManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __await__(self):
        return self.poller.put((self.list_name, self.build_delay_message())).__await__()


class AsyncTaskSubscribeMemory(AsyncTaskSubscribeBase):
    """Memory pub/sub implementation.

    Uses separate queues for each subscriber to implement true pub/sub.
    Each subscriber gets ALL published messages (broadcast pattern).
    """

    def __init__(self, prefix: str = "aiotasks", loop=None):
        super().__init__(prefix=prefix)

        # Each subscriber gets its own queue for true pub/sub
        self._subscriber_queues: list[asyncio.Queue] = []

    async def publish(self, topic, info):
        """Publish message to ALL subscribers (true pub/sub).

        Each subscriber has their own queue and receives a copy of the message.
        This is different from .delay() which uses ONE shared queue.
        """
        message = (
            f"{self.prefix}:{topic}",
            self.build_subscribe_message(**dict(topic=topic, data=info)),
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
        new_queue = asyncio.Queue()
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

    def __init__(
        self,
        dsn=None,
        prefix: str = "aiotasks",
        loop=None,
        concurrency: int = 5,
        max_retries: int = 3,
        task_ttl: int = 3600,
    ):
        super().__init__(
            prefix=prefix,
            concurrency=concurrency,
            max_retries=max_retries,
            task_ttl=task_ttl,
        )

        # Single shared queue - tasks are distributed round-robin to workers
        # Only ONE worker gets each task (correct queue behavior)
        self._task_queue = asyncio.Queue()

        # Track task metadata for cleanup
        self._task_metadata: dict[str, dict] = {}

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

    async def _task_ack(self, task_id: str) -> None:
        """Acknowledge successful task completion for Memory backend.

        Args:
            task_id: Unique identifier for the task.
        """
        await super()._task_ack(task_id)

        # Store ACK in metadata
        import time

        self._task_metadata[task_id] = {
            "status": "ack",
            "timestamp": time.time(),
        }
        log.debug("Memory ACK: Task %s", task_id)

    async def _task_nack(self, task_id: str, error: Exception | None) -> None:
        """Negative acknowledge - task failed for Memory backend.

        Args:
            task_id: Unique identifier for the task.
            error: The exception that caused the failure.
        """
        await super()._task_nack(task_id, error)

        # Store NACK in metadata
        import time

        self._task_metadata[task_id] = {
            "status": "nack",
            "timestamp": time.time(),
            "error": str(error) if error else "Unknown error",
        }
        log.debug("Memory NACK: Task %s - Error: %s", task_id, error)

    async def cleanup_old_tasks(self) -> int:
        """Clean up old task metadata from memory.

        Removes metadata for tasks older than TTL.

        Returns:
            Number of tasks cleaned up.
        """
        import time

        current_time = time.time()
        cleaned = 0

        # Remove tasks older than TTL
        tasks_to_remove = [
            task_id
            for task_id, metadata in self._task_metadata.items()
            if current_time - metadata.get("timestamp", 0) > self.task_ttl
        ]

        for task_id in tasks_to_remove:
            del self._task_metadata[task_id]
            cleaned += 1

        log.debug("Cleaned up %d old task metadata entries", cleaned)
        return cleaned


__all__ = ("AsyncTaskDelayMemory", "AsyncTaskSubscribeMemory")
