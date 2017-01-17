import os
import atexit
import asyncio
import logging
from typing import Union

try:
    import ujson as json
except ImportError:
    import json
    

from .bases import AsyncTaskBase, AsyncTaskSubscribeBase, AsyncTaskDelayBase
from .redis import AsyncTaskDelayRedis, AsyncTaskSubscribeRedis
from .memory import AsyncTaskSubscribeMemory, AsyncTaskDelayMemory

log = logging.getLogger("aiotasks")


if not os.getenv("AIOTASK_DEBUG", False):  # pragma: no cover
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        
        log.debug("uvloop found. Using it as the event loop")
    except ImportError:
        pass
    

# --------------------------------------------------------------------------
# Composed backends
# --------------------------------------------------------------------------
class MemoryBackend(AsyncTaskDelayMemory, AsyncTaskSubscribeMemory, AsyncTaskBase):
    
    def __init__(self, prefix: str = "aoitasks", loop=None):  # pragma: no cover
        self.loop = loop or asyncio.get_event_loop()
        self.prefix = prefix

        AsyncTaskSubscribeMemory.__init__(self, loop=loop)
        AsyncTaskDelayMemory.__init__(self, prefix=prefix, loop=loop)
        AsyncTaskBase.__init__(self)

        # This line is necessary to close redis connections
        atexit.register(self.stop)


class RedisBackend(AsyncTaskSubscribeRedis, AsyncTaskDelayRedis, AsyncTaskBase):
    
    def __init__(self, dsn, prefix: str = "aiotasks", loop=None):
        self.loop = loop or asyncio.get_event_loop()

        AsyncTaskSubscribeRedis.__init__(self, dsn=dsn, prefix=prefix, loop=loop)
        AsyncTaskDelayRedis.__init__(self, dsn=dsn, prefix=prefix, loop=loop)
        AsyncTaskBase.__init__(self)

        # This line is necessary to close redis connections
        atexit.register(self.stop)
        

def build_manager(dsn: str = "memory://",
                  prefix: str = "aiotasks",
                  loop=None) -> Union[AsyncTaskBase, AsyncTaskSubscribeBase, AsyncTaskDelayBase]:
    
    loop = loop or asyncio.get_event_loop()
    
    if not prefix:
        log.error("Empty task_prefix. Using 'aiotasks' as task_prefix")
        prefix = "aiotasks"
    
    # Fixing task_prefix type
    prefix = str(prefix)

    if not os.getenv("AIOTASK_DEBUG", False):  # pragma: no cover
        loop.set_debug(True)
    
    if dsn.startswith("memory"):
        ret = MemoryBackend(prefix=prefix, loop=loop)
    elif dsn.startswith("redis"):
        ret = RedisBackend(dsn=dsn, prefix=prefix, loop=loop)

    # Store manager for global access
    import builtins
    builtins.__aiotasks__ = ret
    
    return ret

__all__ = ("build_manager", )
