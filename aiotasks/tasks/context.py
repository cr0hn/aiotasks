
import abc
import uuid
import asyncio
import logging
import concurrent

from typing import List, Dict

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
        assert len(args) >= 5

        self.fn = args[0]
        self.list_name = args[1]
        self.poller = args[2]
        self.function_name = args[3]
        self.loop = args[4] or asyncio.get_event_loop()
        self.timeout = kwargs.pop("timeout", 0)
        self.infinite_timeout = kwargs.pop("infinite_timeout", 900)

        self.args = args[5:]
        self.kwargs = kwargs

    @abc.abstractmethod
    def __await__(self, *args, **kwargs):  # pragma: no cover
        pass

    async def __aenter__(self):
        # Timeout != 0 -> apply timeout
        try:
            if self.timeout:
                return await asyncio.wait_for(self.fn(*self.args,
                                                      **self.kwargs),
                                              timeout=self.timeout,
                                              loop=self.loop)
            # Timeout == 0 -> infinite --> Apply very long timeout
            else:
                return await asyncio.wait_for(self.fn(*self.args,
                                                      **self.kwargs),
                                              timeout=self.infinite_timeout,
                                              loop=self.loop)

        except concurrent.futures.TimeoutError as e:
            log.error(
                '{function}: {error_message}'.format(function=self.fn.__name__,
                                                     error_message=e))
            raise AioTasksTimeout(e) from e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def build_delay_message(self,
                            task_id: str = None,
                            function_name: str = None,
                            args: List[str] = None,
                            kwargs: Dict = None) -> str:
        """
        If values are not specified, it will be taken from class atributes
        
        :return: message as a string 
        :rtype: str
        """
        if task_id is None:
            task_id = uuid.uuid4().hex

        if function_name is None:
            function_name = self.function_name

        if args is None:
            args = self.args

        if kwargs is None:
            kwargs = self.kwargs

        return msgpack.packb(
            dict(task_id=task_id,
                 function=function_name,
                 args=args,
                 kwargs=kwargs),
            use_bin_type=True)

__all__ = ("AsyncWaitContextManager", )
