import time
import uuid
import asyncio

import msgpack

from aiotasks import build_manager


def test_memory_subscribers_oks(event_loop):

    manager = build_manager(dsn="memory://", loop=event_loop)

    globals()["test_memory_subscribers_oks_finished"] = False

    @manager.subscribe("hello")
    async def task_test_memory_subscribers_oks(topic, data):

        if topic == "hello" and data == "world":
            globals()["test_memory_subscribers_oks_finished"] = True

    async def run():
        manager.run()

        await manager.publish("hello", "world")

        await manager.wait(timeout=0.2, wait_timeout=0.1)

    event_loop.run_until_complete(run())
    manager.stop()

    assert globals()["test_memory_subscribers_oks_finished"] is True

    del globals()["test_memory_subscribers_oks_finished"]


def test_memory_subscribers_no_topics(event_loop):

    manager = build_manager(dsn="memory://", loop=event_loop)

    async def run():
        manager.run()

        await manager.publish("hello", "world")

        await manager.wait(timeout=0.2, exit_on_finish=True, wait_timeout=0.2)

    event_loop.run_until_complete(run())
    manager.stop()

    assert len(manager.topics_subscribers) == 0


def test_memory_subscribers_empty_topics(event_loop):
    import logging

    logger = logging.getLogger("aiotasks")

    class CustomLogger(logging.StreamHandler):
        def __init__(self):
            super(CustomLogger, self).__init__()
            self.content = []

        def emit(self, record):
            self.content.append(record.msg)

    custom = CustomLogger()
    logger.addHandler(custom)

    manager = build_manager(dsn="memory://", loop=event_loop)

    @manager.subscribe()
    async def task_test_memory_subscribers_oks(topic, data):
        if topic == "hello" and data == "world":
            globals()["test_memory_subscribers_oks_finished"] = True

    async def run():
        manager.run()

        await manager.publish("hello", "world")

        await manager.wait(timeout=0.2, exit_on_finish=True, wait_timeout=0.2)

    event_loop.run_until_complete(run())
    manager.stop()

    assert len(manager.topics_subscribers) == 0
    assert "Empty topic fount in function 'task_test_memory_subscribers_oks'. Skipping it." in custom.content


def test_memory_subscribers_duplicated_topics(event_loop):

    manager = build_manager(dsn="memory://", loop=event_loop)

    @manager.subscribe("hello")
    async def task_test_memory_subscribers_oks(topic, data):
        pass

    @manager.subscribe("hello")
    async def task_test_memory_subscribers_oks_2(topic, data):
        pass

    async def run():
        manager.run()

        await manager.publish("hello", "world")

        await manager.wait(timeout=0.2, exit_on_finish=True, wait_timeout=0.1)

    event_loop.run_until_complete(run())
    manager.stop()

    assert len(manager.topics_subscribers) == 1


def test_memory_subscribers_timeout_raises(event_loop):

    manager = build_manager(dsn="memory://", loop=event_loop)

    globals()["test_memory_subscribers_timeout_raises_finished_tasks"] = False

    @manager.subscribe("hello")
    async def task_test_memory_subscribers_oks(topic, data):
        if topic == "hello":
            await asyncio.sleep(data, loop=event_loop)
            globals()["test_memory_subscribers_timeout_raises_finished_tasks"] = True

    async def run():
        manager.run()

        await manager.publish("hello", 5)

        await manager.wait(timeout=0.5, exit_on_finish=True, wait_timeout=0.1)

    event_loop.run_until_complete(run())
    manager.stop()

    assert globals()["test_memory_subscribers_timeout_raises_finished_tasks"] is False

    del globals()["test_memory_subscribers_timeout_raises_finished_tasks"]


