import uuid
import asyncio
import logging

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

from .bases import *
from .context import AsyncWaitContextManager

log = logging.getLogger("aiotasks")


class MemoryAsyncWaitContextManager(AsyncWaitContextManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def __await__(self, *args, **kwargs):
        task_id = uuid.uuid4().hex
        
        return asyncio.ensure_future(self.poller.put((self.list_name,
                                                      msgpack.packb(dict(task_id=task_id,
                                                                         function=self.fn.function_name,
                                                                         args=self.args,
                                                                         kwargs=self.kwargs),
                                                                    use_bin_type=True))),
                                     loop=self.loop).__await__()


class AsyncTaskSubscribeMemory(AsyncTaskSubscribeBase):
    
    def __init__(self,
                 prefix: str = "aiotasks",
                 loop=None):
        super().__init__(prefix, loop)
        
        self._loop_subscribers = loop or asyncio.get_event_loop()
        self.topics_messages = asyncio.Queue(loop=self.loop_subscribers)
    
    async def publish(self, topic, info):
        await self.topics_messages.put(("{}:{}".format(self.prefix, topic),
                                        msgpack.packb(dict(topic=topic,
                                                           data=info),
                                                      use_bin_type=True)))
    
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
    

# --------------------------------------------------------------------------
# Delayers
# --------------------------------------------------------------------------
class AsyncTaskDelayMemory(AsyncTaskDelayBase):
    
    def __init__(self,
                 dsn=None,
                 prefix: str = "aiotasks",
                 loop=None,
                 concurrency: int = 5):
        super().__init__(prefix, loop, concurrency)
        
        self._task_queue = asyncio.Queue(loop=self.loop_delay)
    
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
