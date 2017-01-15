import random
import asyncio

from aiotasks import build_manager


loop = asyncio.get_event_loop()
loop.set_debug(True)

manager = build_manager(dsn="redis://127.0.0.1/0", loop=loop)


@manager.task()
async def task_01(num):
    wait_time = random.randint(1, 5)
    
    print("Task 01 starting: {}. Waiting for {} seconds".format(num, wait_time))
    
    await asyncio.sleep(wait_time, loop=loop)
    
    print("Task 01 stopping")


async def main_async():
    manager.run()
    
    await task_01.delay(1)
    await manager.wait(10)
    
    manager.stop()


if __name__ == '__main__':
    loop.run_until_complete(main_async())
