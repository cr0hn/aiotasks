import asyncio

from aiotasks import build_manager

loop = asyncio.get_event_loop()
loop.set_debug(True)

manager = build_manager(dsn="redis://127.0.0.1/0", loop=loop)


@manager.subscribe("hola")
async def task_01(topic, data):
    print("Task subscribe task_01 - ({}): {}".format(topic, data))
    
    # await asyncio.sleep(2, loop=loop)
    
    print("Task 01 stopping")


@manager.subscribe(["hola", "mundo"])
async def task_02(topic, data):
    print("Task subscribe task_02 - ({}): {}".format(topic, data))
    
    # await asyncio.sleep(2, loop=loop)
    
    print("Task 01 stopping")


async def main_async():
    manager.run()
    
    # await manager.publish("hola", "daaaata")
    for x in range(1000):
        await manager.publish("mundo", "daaaata:{}".format(x))
    await manager.wait(2)
    
    manager.stop()


if __name__ == '__main__':
    loop.run_until_complete(main_async())
