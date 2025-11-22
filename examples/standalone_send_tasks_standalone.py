import asyncio

from aiotasks import build_manager, send_task

manager = build_manager("redis://")


@manager.task()
async def task_01(num):
    print(f"Starting task: {num}")
    await asyncio.sleep(2, loop=manager.loop)
    print(f"Stopping task: {num}")


async def generate_tasks():
    # Generates 5 tasks
    # t = send_task("task_01", 1)
    # await t
    for x in range(5):
        print(f"Iteration: {x}")

        await send_task("task_01", args=(x, ))

if __name__ == '__main__':
    # Start aiotasks for waiting tasks
    manager.run()

    # Launch the task generator. It'll create 5 tasks
    manager.loop.run_until_complete(generate_tasks())

    # Wait until tasks is done
    manager.blocking_wait(exit_on_finish=True)

    # Stop aiotasks listen tasks and shutdown
    manager.stop()
