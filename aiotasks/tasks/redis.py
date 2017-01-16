# -*- coding: utf-8 -*-

import uuid
import logging
import asyncio
import aioredis
import concurrent

from functools import partial
from collections import defaultdict

from .bases import *
from ..helpers import parse_dsn
from ..core.exceptions import AioTasksTimeout

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

log = logging.getLogger("aiotasks")


class AsyncWaitContextManager:
    def __init__(self,
                 *args,
                 **kwargs):  # pragma: no cover
        self.fn = args[0]
        self._list_name = args[1]
        self._redis_poller = args[2]
        self._loop = args[3] or asyncio.get_event_loop()
        self._timeout = kwargs.pop("timeout", 0)
        self._infinite_timeout = kwargs.pop("infinite_timeout", 900)
        
        self.args = args[4:]
        self.kwargs = kwargs
    
    def __await__(self, *args, **kwargs):
        task_id = uuid.uuid4().hex
        
        return self._redis_poller.lpush(self._list_name,
                                        msgpack.packb(dict(task_id=task_id,
                                                           function=self.fn.function_name,
                                                           args=self.args,
                                                           kwargs=self.kwargs),
                                                      use_bin_type=True)).__await__()
    
    async def __aenter__(self):
        # Timeout != 0 -> apply timeout
        try:
            if self._timeout:
                return await asyncio.wait_for(self.fn(*self.args, **self.kwargs),
                                              timeout=self._timeout,
                                              loop=self._loop)
            # Timeout == 0 -> infinite --> Apply very long timeout
            else:
                return await asyncio.wait_for(self.fn(*self.args, **self.kwargs),
                                              timeout=self._infinite_timeout,
                                              loop=self._loop)
        
        except concurrent.futures.TimeoutError as e:
            log.error("{function}: {error_message}".format(function=self.fn.__name__,
                                                           error_message=e))
            raise AioTasksTimeout(e) from e
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# --------------------------------------------------------------------------
# Subscribers
# --------------------------------------------------------------------------
class AsyncTaskSubscribeRedis(AsyncTaskSubscribeBase):
    
    def __init__(self, dsn: str = "redis://127.0.0.1:6379/0",
                 prefix: str = "aiotasks",
                 loop=None):
        self._loop_subscribe = loop or asyncio.get_event_loop()
        self._prefix = prefix
        
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
        
        self.topics_subscribers = defaultdict(set)
        self._topics_channels = dict()
        self._topics_channels = dict()
        self._running_tasks = {}
        self._channel_processors = set()
        self._ready = asyncio.Event(loop=self.loop_subscribers)
    
    async def _channel_listener(self, channel):
        
        # Mark ready OK
        self._ready.set()
        
        while await channel.wait_message():
            raw = await channel.get()
            
            msg = msgpack.unpackb(raw, encoding='utf-8')
            
            topic = msg.get("topic")
            info = msg.get("data")
            
            for fn in self.topics_subscribers[topic]:
                task = self.loop_subscribers.create_task(fn(topic, info))
                
                # Build stop task
                task_id = uuid.uuid4().hex
                done_fn = partial(self._make_tasks_done_subscriber, task_id)
                
                task.add_done_callback(done_fn)
                
                self._running_tasks[task_id] = task
    
    async def _subscribe(self, topics: set):
        for topic in topics:
            
            channels = await self._redis_sub.subscribe("{}:{}".format(self._prefix, topic))
            
            self._topics_channels[topic] = channels[0]
            
            self._channel_processors.add(self.loop_subscribers.create_task(self._channel_listener(channels[0])))
        
        if not topics:
            # Mark ready OK
            self._ready.set()
    
    def subscribe(self, topics=None):
        """Decorator"""
        
        if not topics:
            topics = set()
        
        if isinstance(topics, str):
            topics = {topics}
        
        def real_decorator(f):
            # if function is a coro, add some new functions
            if asyncio.iscoroutinefunction(f):
                if not topics:
                    log.error("Empty topic fount in function '{}'. Skipping it.".format(f.__name__))
                for topic in topics:
                    self.topics_subscribers[topic].add(f)
            return f
        
        return real_decorator
    
    async def publish(self, topic, info):
        # Wait for channel listener
        if not self._ready.is_set():
            await self._ready.wait()
        
        await self._redis_pub.publish("{}:{}".format(self._prefix, topic),
                                      msgpack.packb(dict(topic=topic, data=info),
                                                    use_bin_type=True))
    
    async def has_pending_topics(self):
        return bool(self._running_tasks)
    
    def _make_tasks_done_subscriber(self, task_id, future):
        self._running_tasks.pop(task_id)
    
    async def listen_topics(self):
        # Build channels
        await self.loop_subscribers.create_task(self._subscribe(set(self.topics_subscribers.keys())))
    
    def stop_subscriptions(self):
        for p in self._channel_processors:
            p.cancel()
        
        self._redis_sub.close()
        self._redis_pub.close()
        
        if not self.loop_subscribers.is_closed():
            self.loop_subscribers.run_until_complete(self._redis_sub.wait_closed())
            self.loop_subscribers.run_until_complete(self._redis_pub.wait_closed())
    
    @property
    def loop_subscribers(self):
        return self._loop_subscribe


# --------------------------------------------------------------------------
# Delayers
# --------------------------------------------------------------------------
class AsyncTaskDelayRedis(AsyncTaskDelayBase):
    
    def __init__(self, dsn: str = "redis://127.0.0.1:6379/0",
                 prefix: str = "aiotasks",
                 redis_connection=None,
                 redis_poller=None,
                 concurrency: int = 5,
                 loop=None):
        self._loop_delay = loop or asyncio.new_event_loop()
        self._concurrency = concurrency
        self._prefix = prefix
        
        _, password, host, port, db = parse_dsn(dsn)
        
        if not port:
            port = 6379
        
        port = int(port)
        if not db:
            db = 0
        
        self._redis_consumer = redis_connection
        if not self._redis_consumer:
            self._redis_consumer = self.loop_delay.run_until_complete(aioredis.create_redis(address=(host, port),
                                                                                            db=db,
                                                                                            password=password,
                                                                                            loop=self.loop_delay))
        
        self._redis_poller = redis_poller
        if not self._redis_poller:
            self._redis_poller = self.loop_delay.run_until_complete(aioredis.create_redis(address=(host, port),
                                                                                          db=db,
                                                                                          password=password,
                                                                                          loop=self.loop_delay))
        
        # Create the task channel in redis
        self._list_name = "{}:{}".format(self._prefix, "tasks")
        
        self._tasks = dict()  # Tasks descriptors
        self._running_tasks = dict()
        
        # Semaphore for concurrency
        self._concurrency_sem = asyncio.BoundedSemaphore(self._concurrency,
                                                         loop=self.loop_delay)
    
    def task(self, name: str = None):
        """Decorator"""
        
        def real_decorator(f):
            # Real call to funcion
            def new_f(*args, **kwargs):
                return f(*args, **kwargs)
            
            # if function is a coro, add some new functions
            if asyncio.iscoroutinefunction(f):
                new_f.delay = partial(AsyncWaitContextManager,
                                      new_f,
                                      self._list_name,
                                      self._redis_poller,
                                      self.loop_delay)
                
                if name:
                    function_name = name
                else:
                    function_name = f.__name__
                
                new_f.function_name = function_name
                
                self._tasks[function_name] = f
            
            return new_f
        
        return real_decorator
    
    def add_task(self, function: callable, name: str = None) -> callable:
        if not asyncio.iscoroutinefunction(function):
            log.warning("Function '{}' is not a coroutine and can't be added as a task".format(function.__name__))
            return

        function.delay = partial(AsyncWaitContextManager,
                              function,
                              self._list_name,
                              self._redis_poller,
                              self.loop_delay)
        
        if name:
            function_name = name
        else:
            function_name = function.__name__
        
        function.function_name = function_name
        
        self._tasks[function_name] = function
    
    async def has_pending_tasks(self):
        return bool(self._running_tasks) or not bool(await self._redis_poller.llen(self._list_name))
    
    def _make_tasks_done_delay(self, running_task, future):
        self._running_tasks.pop(running_task)
        self._concurrency_sem.release()
    
    async def listen_tasks(self):
        
        while True:
            raw_data = await self._redis_consumer.brpop(self._list_name, timeout=0)
            
            # Limit concurrent executions
            await self._concurrency_sem.acquire()
            
            _, raw = raw_data
            
            msg = msgpack.unpackb(raw, encoding='utf-8')
            args = msg.get("args")
            kwargs = msg.get("kwargs")
            task_id = msg.get("task_id")
            function = msg.get("function")
            
            try:
                if type(task_id) is int:
                    task_id = str(task_id)
                
                uuid.UUID(task_id, version=4)
            except ValueError:
                log.error("Task ID '{}' has not valid UUID4 format".format(task_id))
            
            try:
                local_task = self._tasks[function]
            except KeyError:
                log.warning("No local task with name '{}'".format(function))
                continue
            
            task = self.loop_delay.create_task(local_task(*args, **kwargs))
            running_task_id = uuid.uuid4().hex
            
            # Build stop task
            done_fn = partial(self._make_tasks_done_delay, running_task_id)
            
            task.add_done_callback(done_fn)
            
            self._running_tasks[running_task_id] = task
    
    def stop_delayers(self):
        self._redis_consumer.close()
        self._redis_poller.close()
        
        for t in self._running_tasks.values():
            t.cancel()
        
        if not self.loop_delay.is_closed():
            self.loop_delay.run_until_complete(self._redis_consumer.wait_closed())
            self.loop_delay.run_until_complete(self._redis_poller.wait_closed())
    
    @property
    def loop_delay(self):
        return self._loop_delay

__all__ = ("AsyncTaskSubscribeRedis", "AsyncTaskDelayRedis")
