import asyncio

from aiotasks import build_manager


loop = asyncio.get_event_loop()
loop.set_debug(True)

manager = build_manager(loop=loop)


@manager.task()
async def task_01(num):
    print("Task 01 starting: {}".format(num))
    
    await asyncio.sleep(2, loop=loop)
    
    print("Task 01 stopping")


async def main_async():
    manager.run()
    
    await task_01.delay(1)
    await manager.wait(5)
    
    manager.stop()


if __name__ == '__main__':
    loop.run_until_complete(main_async())
