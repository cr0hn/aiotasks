import asyncio
import random

from aiotasks import build_manager

loop = asyncio.get_event_loop()
loop.set_debug(True)

manager = build_manager(dsn="redis://127.0.0.1/0", loop=loop)


@manager.task()
async def task_01(num):
    # wait_time = random.randint(1,)
    wait_time = 0.01

    print(f"Task {num}. Waiting for {wait_time} seconds")

    await asyncio.sleep(wait_time, loop=loop)

    print(f"Task {num} stopping")


async def main_async():
    for i in range(1000):
        print(f"T{i}")
        await task_01.delay(random.randint(1, 100))

if __name__ == '__main__':
    loop.run_until_complete(main_async())
