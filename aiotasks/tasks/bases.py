import abc
import time
import uuid
import asyncio
import logging

from functools import partial
from collections import defaultdict

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack

log = logging.getLogger("aiotasks")


# --------------------------------------------------------------------------
# Base classes
# --------------------------------------------------------------------------
class AsyncTaskSubscribeBase(metaclass=abc.ABCMeta):
    
    def __init__(self,
                 prefix: str = "aiotasks",
                 loop=None):
        self.loop_subscribers = loop or asyncio.get_event_loop()
        self.prefix = prefix

        self.running_tasks = dict()
        self.topics_subscribers = defaultdict(set)
        self.subscriber_ready = asyncio.Event(loop=self.loop_subscribers)
    
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
    
    @abc.abstractmethod
    async def wait_for_message(self, channel):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def get_next_message(self, channel) -> object:  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def register_topics(self):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def publish(self, topic, info):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def has_pending_topics(self):  # pragma: no cover
        pass

    def _make_tasks_done_subscriber(self, task_id, future):
        self.running_tasks.pop(task_id)

    async def listen_topics(self):
        # Mark ready OK
        self.subscriber_ready.set()
    
        channel = await self.register_topics()
    
        while await self.wait_for_message(channel):
            raw = await self.get_next_message(channel)
        
            if hasattr(raw, "__iter__") and len(raw) != 2:
                log.error("Invalid data from Redis subscriber. It must be a tuple with len 2")
        
            ch, data = raw
        
            if hasattr(ch, 'decode'):
                ch = ch.decode()
        
            # Get topic
            try:
                prefix, topic = ch.split(":", maxsplit=1)
            except ValueError:
                log.error("Invalid channel name: {}".format(ch))
                continue
        
            # Check prefix
            if prefix != self.prefix:
                log.error("Invalid prefix: {}".format(prefix))
                continue
                
            if hasattr(data, "encode"):
                data = data.encode()
        
            msg = msgpack.unpackb(data, encoding='utf-8')
            data_topic = msg.get("topic", False)
            data_content = msg.get("data", False)
        
            if not data_topic or not data_content:
                log.error("Invalid data topic / data content - topic: {} / data: {}".format(data_topic, data_content))
                continue
        
            for fn in self.topics_subscribers.get(topic, tuple()):
                # Build stop task
                task_id = uuid.uuid4().hex
                done_fn = partial(self._make_tasks_done_subscriber, task_id)
            
                task = self.loop_subscribers.create_task(fn(data_topic, data_content))
                task.add_done_callback(done_fn)
            
                self.running_tasks[task_id] = task

    @abc.abstractmethod
    def stop_subscriptions(self):  # pragma: no cover
        pass
    

class AsyncTaskDelayBase(metaclass=abc.ABCMeta):
    
    # --------------------------------------------------------------------------
    # Implemented methods
    # --------------------------------------------------------------------------
    def __init__(self,
                 prefix: str = "aiotasks",
                 loop=None,
                 concurrency: int = 5):
        
        self.task_prefix = prefix
        self.task_running_tasks = dict()
        self.task_available_tasks = dict()
        self.task_concurrency = concurrency
        self.loop_delay = loop or asyncio.new_event_loop()
        self.task_list_name = "{}:{}".format(self.task_prefix, "tasks")
        
        # Semaphore for task_concurrency
        self.task_concurrency_sem = asyncio.BoundedSemaphore(self.task_concurrency,
                                                             loop=self.loop_delay)

    def task(self, name: str = None):
        """Decorator"""
    
        def real_decorator(f):
            # Real call to funcion
            def new_f(*args, **kwargs):
                return f(*args, **kwargs)
        
            # if function is a coro, add some new functions
            if asyncio.iscoroutinefunction(f):
                new_f.delay = partial(self.context_class,
                                      new_f,
                                      self.task_list_name,
                                      self.poller,
                                      self.loop_delay)
            
                if name:
                    function_name = name
                else:
                    function_name = f.__name__
            
                new_f.function_name = function_name
            
                self.task_available_tasks[function_name] = f
        
            return new_f
    
        return real_decorator

    def add_task(self, function: callable, name: str = None) -> callable:
        if not asyncio.iscoroutinefunction(function):
            log.warning("Function '{}' is not a coroutine and can't be added as a task".format(function.__name__))
            return
    
        function.delay = partial(self.context_class,
                                 function,
                                 self.task_list_name,
                                 self.poller,
                                 self.loop_delay)
    
        if name:
            function_name = name
        else:
            function_name = function.__name__
    
        function.function_name = function_name
    
        self.task_available_tasks[function_name] = function

    def _make_tasks_done_delay(self, running_task, future):
        self.task_running_tasks.pop(running_task)
        self.task_concurrency_sem.release()
    
        if hasattr(self, "custom_task_done"):
            self.custom_task_done(running_task)

    async def listen_tasks(self):
        while True:
            raw_data = await self.pending_tasks
        
            # Limit concurrent executions
            await self.task_concurrency_sem.acquire()
        
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
                continue
        
            try:
                local_task = self.task_available_tasks[function]
            except KeyError:
                log.warning("No local task with name '{}'".format(function))
                continue
        
            running_task_id = uuid.uuid4().hex
            done_fn = partial(self._make_tasks_done_delay, running_task_id)
        
            # Build stop task
            task = self.loop_delay.create_task(local_task(*args, **kwargs))
            task.add_done_callback(done_fn)
        
            self.task_running_tasks[running_task_id] = task

    # --------------------------------------------------------------------------
    # Abstract methods & properties
    # --------------------------------------------------------------------------
    @abc.abstractmethod
    async def poller(self):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def has_pending_tasks(self):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    def stop_delayers(self):  # pragma: no cover
        pass

    # --------------------------------------------------------------------------
    # Properties
    # --------------------------------------------------------------------------
    @abc.abstractproperty
    def pending_tasks(self):  # pragma: no cover
        pass
    
    @abc.abstractproperty
    def context_class(self):  # pragma: no cover
        pass


class AsyncTaskBase(object, metaclass=abc.ABCMeta):
    def __init__(self):
        self._launcher_tasks = None
        self._launcher_topics = None
    
    async def wait(self, *, timeout: float = 0, exit_on_finish: bool = False, wait_timeout: float = 1.0):
        """
        :param exit_on_finish: exit when all pending tasks are finished
        :type exit_on_finish: bool
        
        :param timeout: Time in seconds
        :type timeout: int
        """
        TIME_STEP = wait_timeout
        
        _infinite = False
        if timeout == 0:
            _infinite = True
        _start_time = time.time()
        
        while True:
            _has_pending_tasks = await self.has_pending_tasks()
            _has_pending_topics = await self.has_pending_topics()
            
            # There are pending tasks?
            if _has_pending_tasks or _has_pending_topics:
                # Yes, there's pending tasks, but is timeout reached?
                if time.time() - _start_time > timeout and not _infinite:
                    return
            else:
                
                # No tasks pending and marked -> If marked as a exit on tasks finished
                if exit_on_finish:
                    return
                
                # NO, there's not pending tasks, but is timeout reached?
                if time.time() - _start_time > timeout and not _infinite:
                    return
            
            # Wait
            await asyncio.sleep(TIME_STEP, loop=self.loop)
    
    def stop(self):
        self.stop_delayers()
        self.stop_subscriptions()
        
        if self._launcher_topics:
            self._launcher_topics.cancel()
        if self._launcher_tasks:
            self._launcher_tasks.cancel()

        if not self.loop_delay.is_closed():
            self.loop_delay.run_until_complete(asyncio.wait([self._launcher_tasks], loop=self.loop_delay))
        if not self.loop_subscribers.is_closed():
            self.loop_subscribers.run_until_complete(asyncio.wait([self._launcher_topics], loop=self.loop_subscribers))

    def run(self):
        """Blocking run"""
        self._launcher_topics = self.loop_subscribers.create_task(self.listen_topics())
        self._launcher_tasks = self.loop_delay.create_task(self.listen_tasks())


__all__ = ("AsyncTaskSubscribeBase", "AsyncTaskDelayBase", "AsyncTaskBase")
