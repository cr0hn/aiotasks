import abc
import time
import asyncio


# --------------------------------------------------------------------------
# Base classes
# --------------------------------------------------------------------------
class AsyncTaskSubscribeBase(metaclass=abc.ABCMeta):
    # Decorator
    @abc.abstractmethod
    def subscribe(self, topics=None):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def publish(self, topic, info):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def has_pending_topics(self):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def listen_topics(self):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    def stop_subscriptions(self):  # pragma: no cover
        pass
    
    @abc.abstractproperty
    def loop_subscribers(self):  # pragma: no cover
        pass


class AsyncTaskDelayBase(metaclass=abc.ABCMeta):
    
    # Decorator
    @abc.abstractmethod
    def task(self, name: str = None):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    def add_task(self, function: callable, name: str = None):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def has_pending_tasks(self):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    async def listen_tasks(self):  # pragma: no cover
        pass
    
    @abc.abstractmethod
    def stop_delayers(self):  # pragma: no cover
        pass
    
    @abc.abstractproperty
    def loop_delay(self):  # pragma: no cover
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
    
    def run(self):
        """Blocking run"""
        self._launcher_topics = self.loop_subscribers.create_task(self.listen_topics())
        self._launcher_tasks = self.loop_delay.create_task(self.listen_tasks())


__all__ = ("AsyncTaskSubscribeBase", "AsyncTaskDelayBase", "AsyncTaskBase")
