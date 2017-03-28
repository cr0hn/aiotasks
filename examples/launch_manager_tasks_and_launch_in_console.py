import asyncio

from aiotasks import build_manager

#
# We can't use memory backend when consume tasks using binary in
# another process, because it can't share Queue memory for sharing
# Tasks info
#
manager = build_manager(dsn="redis://")


@manager.task()
async def task_01(num):
    print("Task 01 starting: {}".format(num))
    await asyncio.sleep(2, loop=manager.loop)
    print("Task 01 stopping")


async def generate_tasks():
    # Generates 5 tasks
    for x in range(5):
        await task_01.delay(x)

if __name__ == '__main__':
    # Launch the task generator. It'll create 5 tasks
    manager.loop.run_until_complete(generate_tasks())
