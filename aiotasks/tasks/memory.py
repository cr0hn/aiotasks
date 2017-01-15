import uuid
import asyncio
import logging

from functools import partial
from collections import defaultdict

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

from .bases import *

log = logging.getLogger("aiotasks")


class AsyncWaitContextManager:
    def __init__(self, *args, **kwargs):
        self.fn = args[0]
        self.args = args[1:]
        self.kwargs = kwargs
    
    async def __aenter__(self):
        resp = await self.fn(*self.args, **self.kwargs)
        
        return resp
    
    async def __aexit__(self, exc_type, exc, tb):
        pass


# --------------------------------------------------------------------------
# Subscribers
# --------------------------------------------------------------------------
class AsyncTaskSubscribeMemory(AsyncTaskSubscribeBase):

    def __init__(self, loop=None):
        self._loop_subscribers = loop or asyncio.get_event_loop()
        
        self._running_tasks = {}
        
        self.topics_subscribers = defaultdict(set)
        self.topics_messages = asyncio.Queue(loop=self.loop_subscribers)
    
    def subscribe(self, topics=None):
        """Decorator"""
        
        if not topics:
            topics = set()
        if isinstance(topics, str):
            topics = {topics}
        
        def real_decorator(f):
            
            # if function is a coro, add some new functions
            if asyncio.iscoroutinefunction(f):
                for topic in topics:
                    self.topics_subscribers[topic].add(f)
            
            return f
        
        return real_decorator
    
    async def publish(self, topic, info):
        await self.topics_messages.put((topic, info))

    async def has_pending_topics(self):
        return not self.topics_messages.empty()
    
    def _make_tasks_done_subscriber(self, task_id, future):
        self._running_tasks.pop(task_id)
    
    async def listen_topics(self):
        while True:
            topic, info = await self.topics_messages.get()
            
            # Get all functions subscrited to a topic
            for fn in self.topics_subscribers[topic]:
                task = self.loop_subscribers.create_task(fn(topic, info))
                
                # Build stop task
                done_fn = partial(self._make_tasks_done_subscriber, id(task))
                
                task.add_done_callback(done_fn)
                
                self._running_tasks[id(task)] = task
    
    def stop_subscriptions(self):
        for t in self._running_tasks.values():
            t.cancel()

    @property
    def loop_subscribers(self):
        return self._loop_subscribers


# --------------------------------------------------------------------------
# Delayers
# --------------------------------------------------------------------------
class AsyncTaskDelayMemory(AsyncTaskDelayBase):

    def __init__(self,
                 loop=None,
                 concurrency: int = 5):
        self._concurrency = concurrency
        
        self._loop_delay = loop or asyncio.get_event_loop()
        self.pending_tasks = asyncio.Queue(loop=self.loop_delay)
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
                new_f.delay = partial(self._delay, new_f)
                new_f.wait = partial(AsyncWaitContextManager, new_f)

                if name:
                    function_name = name
                else:
                    function_name = f.__name__
    
                new_f.function_name = function_name

            return new_f
        
        return real_decorator

    def add_task(self, function: callable, name: str = None) -> callable:
        if not asyncio.iscoroutinefunction(function):
            log.warning("Function '{}' is not a coroutine and can't be added as a task".format(function.__name__))
            return
    
        function.delay = partial(self._delay, function)
        function.wait = partial(AsyncWaitContextManager, function, loop=self.loop_delay)
    
        if name:
            function_name = name
        else:
            function_name = function.__name__
    
        function.function_name = function_name

    async def _delay(self, function, *args, **kwargs):
        task_id = uuid.uuid4().hex
        
        await self.pending_tasks.put(dict(task_id=task_id,
                                          function=function.function_name,
                                          args=args,
                                          kwargs=kwargs))

    async def has_pending_tasks(self):
        return not self.pending_tasks.empty() or bool(self._running_tasks)
    
    def _make_tasks_done_delay(self, task_id, future):
        self._running_tasks.pop(task_id)
        self._concurrency_sem.release()
    
    async def listen_tasks(self):
        while True:
            raw = await self.pending_tasks.get()

            # Limit concurrent executions
            await self._concurrency_sem.acquire()

            msg = msgpack.unpackb(raw)

            args = msg.get("args")
            kwargs = msg.get("kwargs")
            task_id = msg.get("task_id")
            function = msg.get("function")
            
            # Build task
            task = self.loop_delay.create_task(fn(*args, **kwargs))
            
            # Build stop task
            done_fn = partial(self._make_tasks_done_delay, id(task))
            
            task.add_done_callback(done_fn)
            
            self._running_tasks[id(task)] = task
    
    def stop_delayers(self):
        for t in self._running_tasks.values():
            t.cancel()

    @property
    def loop_delay(self):
        return self._loop_delay
    

__all__ = ("AsyncTaskSubscribeMemory", "AsyncTaskDelayMemory")
