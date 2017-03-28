import asyncio

from aiotasks import build_manager


manager = build_manager("redis://")


@manager.subscribe("my_topic")
async def task_01(topic, data):
    print("Task subscribe task_01 - ({}): {}".format(topic, data))
    
    await asyncio.sleep(2, loop=manager.loop)


@manager.subscribe("other_topic")
async def task_other(topic, data):
    print("Task subscribe task_other - ({}): {}".format(topic, data))
    
    await asyncio.sleep(2, loop=manager.loop)


async def generate_tasks():
    # Generates 5 tasks
    for x in range(5):
        await manager.publish("my_topic", "heeeelloo:{}".format(x))
    
    # Generates 5 tasks
    for x in range(5):
        await manager.publish("other_topic", "XXXXX:{}".format(x))

if __name__ == '__main__':
    # Start aiotasks for waiting tasks
    manager.run()

    # Launch the task generator. It'll create 5 tasks
    manager.loop.run_until_complete(generate_tasks())

    # Wait until tasks is done
    manager.blocking_wait(exit_on_finish=True)

    # Stop aiotasks listen tasks and shutdown
    manager.stop()
