import abc
import uuid
import asyncio
import logging
import concurrent


try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack
    
from ..core.exceptions import AioTasksTimeout


log = logging.getLogger("aiotasks")


class AsyncWaitContextManager:
    
    def __init__(self,
                 *args,
                 **kwargs):
        self.fn = args[0]
        self.list_name = args[1]
        self.poller = args[2]
        self.loop = args[3] or asyncio.get_event_loop()
        self.timeout = kwargs.pop("timeout", 0)
        self.infinite_timeout = kwargs.pop("infinite_timeout", 900)
        
        self.args = args[4:]
        self.kwargs = kwargs
    
    @abc.abstractmethod
    def __await__(self, *args, **kwargs):  # pragma: no cover
        pass

    async def __aenter__(self):
        # Timeout != 0 -> apply timeout
        try:
            if self.timeout:
                return await asyncio.wait_for(self.fn(*self.args, **self.kwargs),
                                              timeout=self.timeout,
                                              loop=self.loop)
            # Timeout == 0 -> infinite --> Apply very long timeout
            else:
                return await asyncio.wait_for(self.fn(*self.args, **self.kwargs),
                                              timeout=self.infinite_timeout,
                                              loop=self.loop)
        
        except concurrent.futures.TimeoutError as e:
            log.error("{function}: {error_message}".format(function=self.fn.__name__,
                                                           error_message=e))
            raise AioTasksTimeout(e) from e
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    
__all__ = ("AsyncWaitContextManager", )
