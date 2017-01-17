# -*- coding: utf-8 -*-

import uuid
import logging
import asyncio
import aioredis

from functools import partial
from collections import defaultdict

from .bases import *
from ..helpers import parse_dsn
from .context import AsyncWaitContextManager

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

log = logging.getLogger("aiotasks")


class RedisAsyncWaitContextManager(AsyncWaitContextManager):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __await__(self, *args, **kwargs):
        task_id = uuid.uuid4().hex
        
        return self.poller.lpush(self.list_name,
                                 msgpack.packb(dict(task_id=task_id,
                                                    function=self.fn.function_name,
                                                    args=self.args,
                                                    kwargs=self.kwargs),
                                               use_bin_type=True)).__await__()
    

# --------------------------------------------------------------------------
# Subscribers
# --------------------------------------------------------------------------
class AsyncTaskSubscribeRedis(AsyncTaskSubscribeBase):
    
    def __init__(self,
                 dsn: str = "redis://127.0.0.1:6379/0",
                 prefix: str = "aiotasks",
                 loop=None):
        super().__init__(prefix, loop)
        
        _, password, host, port, db = parse_dsn(dsn)
        
        if not port:
            port = 6379
        
        port = int(port)
        if not db:
            db = 0
        
        self._redis_pub = self.loop_subscribers.run_until_complete(aioredis.create_redis(address=(host, port),
                                                                                         db=db,
                                                                                         password=password,
                                                                                         loop=self.loop_subscribers))
        
        self._redis_sub = self.loop_subscribers.run_until_complete(aioredis.create_redis(address=(host, port),
                                                                                         db=db,
                                                                                         password=password,
                                                                                         loop=self.loop_subscribers))
        
    async def publish(self, topic, info):
        # Wait for channel listener
        if not self.subscriber_ready.is_set():
            await self.subscriber_ready.wait()
        
        await self._redis_pub.publish("{}:{}".format(self.prefix, topic),
                                      msgpack.packb(dict(topic=topic, data=info),
                                                    use_bin_type=True))
    
    async def has_pending_topics(self):
        return bool(self.running_tasks)
    
    async def register_topics(self):
        channels = await self._redis_sub.psubscribe("{}:*".format(self.prefix))
        return channels[0]
    
    async def wait_for_message(self, channel):
        return await channel.wait_message()
        
    async def get_next_message(self, channel):
        return await channel.get()
        
    def stop_subscriptions(self):
        self._redis_sub.close()
        self._redis_pub.close()
        
        if not self.loop_subscribers.is_closed():
            self.loop_subscribers.run_until_complete(self._redis_sub.wait_closed())
            self.loop_subscribers.run_until_complete(self._redis_pub.wait_closed())
    

# --------------------------------------------------------------------------
# Delayers
# --------------------------------------------------------------------------
class AsyncTaskDelayRedis(AsyncTaskDelayBase):
    
    def __init__(self,
                 dsn: str = "redis://127.0.0.1:6379/0",
                 prefix: str = "aiotasks",
                 concurrency: int = 5,
                 loop=None):
        super().__init__(prefix, loop, concurrency)
        
        _, password, host, port, db = parse_dsn(dsn)
        
        if not port:
            port = 6379
        
        port = int(port)
        if not db:
            db = 0
        
        self._redis_consumer = self.loop_delay.run_until_complete(aioredis.create_redis(address=(host, port),
                                                                                        db=db,
                                                                                        password=password,
                                                                                        loop=self.loop_delay))
        
        self._redis_poller = self.loop_delay.run_until_complete(aioredis.create_redis(address=(host, port),
                                                                                      db=db,
                                                                                      password=password,
                                                                                      loop=self.loop_delay))
    
    async def has_pending_tasks(self):
        return bool(self.task_running_tasks) or not bool(await self._redis_poller.llen(self.task_list_name))
        
    def stop_delayers(self):
        self._redis_consumer.close()
        self._redis_poller.close()
        
        for t in self.task_running_tasks.values():
            t.cancel()
        
        if not self.loop_delay.is_closed():
            self.loop_delay.run_until_complete(self._redis_consumer.wait_closed())
            self.loop_delay.run_until_complete(self._redis_poller.wait_closed())
    
    @property
    def poller(self):
        return self._redis_poller
    
    @property
    def context_class(self):
        return RedisAsyncWaitContextManager
    
    @property
    def pending_tasks(self):
        return self._redis_consumer.brpop(self.task_list_name, timeout=0)
    

__all__ = ("AsyncTaskSubscribeRedis", "AsyncTaskDelayRedis")
