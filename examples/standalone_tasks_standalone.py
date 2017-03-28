import asyncio

from aiotasks import build_manager


manager = build_manager("redis://")


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
    # Start aiotasks for waiting tasks
    manager.run()

    # Launch the task generator. It'll create 5 tasks
    manager.loop.run_until_complete(generate_tasks())

    # Wait until tasks is done
    manager.blocking_wait(exit_on_finish=True)

    # Stop aiotasks listen tasks and shutdown
    manager.stop()
