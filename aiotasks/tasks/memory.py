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

    def __init__(self,
                 prefix: str = "aiotasks",
                 loop=None):
        super().__init__(loop=loop, prefix=prefix)

        self._loop_subscribers = loop or asyncio.get_event_loop()
        self.topics_messages = asyncio.Queue(loop=self._loop_subscribers)

    async def publish(self, topic, info):
        await self.topics_messages.put(
            (
                "{}:{}".format(self.prefix, topic),
                self.build_subscribe_message(**dict(topic=topic, data=info))
            )
        )

    async def has_pending_topics(self):
        return not self.topics_messages.empty()

    async def register_topics(self):
        pass

    async def wait_for_message(self, channel):
        return True

    async def get_next_message(self, channel):
        return await self.topics_messages.get()

    def stop_subscriptions(self):
        for t in self.running_tasks.values():
            t.cancel()


# -------------------------------------------------------------------------
# Delayers
# -------------------------------------------------------------------------
class AsyncTaskDelayMemory(AsyncTaskDelayBase):

    def __init__(self,
                 dsn=None,
                 prefix: str = "aiotasks",
                 loop=None,
                 concurrency: int = 5):
        super().__init__(loop=loop, prefix=prefix, concurrency=concurrency)

        self._task_queue = asyncio.Queue(loop=self._loop_delay)

    async def has_pending_tasks(self):
        return not self._task_queue.empty() or bool(self.task_running_tasks)

    def custom_task_done(self, task_id):
        self._task_queue.task_done()

    def stop_delayers(self):
        for t in self.task_running_tasks.values():
            t.cancel()

    @property
    def pending_tasks(self):
        return self._task_queue.get()

    @property
    def context_class(self):
        return MemoryAsyncWaitContextManager

    @property
    def poller(self):
        return self._task_queue


__all__ = ("AsyncTaskSubscribeMemory", "AsyncTaskDelayMemory")
