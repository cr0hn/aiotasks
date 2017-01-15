import random
import asyncio

from aiotasks import build_manager

event_loop = asyncio.new_event_loop()

manager = build_manager(dsn="redis://127.0.0.1/1", loop=event_loop)

globals()["test_redis_delay_oks_finished"] = False


@manager.task()
async def task_test_redis_delay_oks(num):
    await asyncio.sleep(0.1, loop=event_loop)
    print("#" * 50)
    globals()["test_redis_delay_oks_finished"] = True


async def run():
    manager.run()
    
    # await task_test_redis_delay_oks.delay(1)

    for x in range(10):
        print("POOLING")
        t = await manager._redis_poller.strlen(manager._list_name)
        
        print("RESULT: ", t)
        
        await asyncio.sleep(0.5, loop=event_loop)
    
    # await manager.wait(timeout=5, exit_on_finish=True, wait_timeout=0.5)


if __name__ == '__main__':
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert globals()["test_redis_delay_oks_finished"] is True
    
    del globals()["test_redis_delay_oks_finished"]
