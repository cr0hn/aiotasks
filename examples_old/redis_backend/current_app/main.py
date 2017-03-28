import time
import uuid
import asyncio

import msgpack

from aiotasks import build_manager

from subapp import *

manager = build_manager(dsn="redis://127.0.0.1")


@manager.task()
async def task_test_redis_delay_oks(num):
    globals()["test_redis_delay_oks_finished"] = True


async def run():
    manager.run()
    
    await task_test_redis_delay_oks.delay(1)
    
    await manager.wait(timeout=1, exit_on_finish=True, wait_timeout=0.2)


if __name__ == '__main__':
    manager.loop.run_until_complete(run())
    
    hola()
    manager.stop()