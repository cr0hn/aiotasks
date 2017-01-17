import pytest
import asyncio

from aiotasks import build_manager, AioTasksTimeout


def test_memory_wait_oks(event_loop):

    manager = build_manager(dsn="memory://", loop=event_loop)

    globals()["test_memory_wait_oks_finished"] = False

    @manager.task()
    async def task_test_memory_wait_oks():
        return True

    async def run():
        manager.run()

        async with task_test_memory_wait_oks.delay() as f:
            globals()["test_memory_wait_oks_finished"] = f

    event_loop.run_until_complete(run())
    manager.stop()

    assert globals()["test_memory_wait_oks_finished"] == True

    del globals()["test_memory_wait_oks_finished"]


def test_memory_wait_timeout_raises(event_loop):

    manager = build_manager(dsn="memory://", loop=event_loop)

    globals()["test_memory_wait_timeout_raises_finished"] = False

    @manager.task()
    async def task_test_memory_wait_oks():
        await asyncio.sleep(2, loop=event_loop)

        return True

    async def run():
        manager.run()

        try:
            async with task_test_memory_wait_oks.delay(timeout=0.2) as f:
                pass
        except AioTasksTimeout:
                globals()["test_memory_wait_timeout_raises_finished"] = True

    event_loop.run_until_complete(run())
    manager.stop()

    assert globals()["test_memory_wait_timeout_raises_finished"] is True

    del globals()["test_memory_wait_timeout_raises_finished"]


def test_memory_wait_infinite_timeout_raises(event_loop):

    manager = build_manager(dsn="memory://", loop=event_loop)

    globals()["test_memory_wait_infinite_timeout_raises_finished"] = False

    @manager.task()
    async def task_test_memory_wait_oks():
        await asyncio.sleep(2, loop=event_loop)

        return True

    async def run():
        manager.run()
        try:
            async with task_test_memory_wait_oks.delay(infinite_timeout=0.2) as f:
                globals()["test_memory_wait_infinite_timeout_raises_finished"] = f
        except AioTasksTimeout:
            globals()["test_memory_wait_timeout_raises_finished"] = True

    event_loop.run_until_complete(run())
    manager.stop()

    assert globals()["test_memory_wait_infinite_timeout_raises_finished"] == False

    del globals()["test_memory_wait_infinite_timeout_raises_finished"]


def test_memory_wait_infinite_raises_timeout_exception(event_loop):

    manager = build_manager(dsn="memory://", loop=event_loop)

    globals()["test_memory_wait_infinite_timeout_raises_finished"] = False

    @manager.task()
    async def task_test_memory_wait_oks():
        await asyncio.sleep(2, loop=event_loop)

        return True

    async def run():
        manager.run()
        with pytest.raises(AioTasksTimeout):
            async with task_test_memory_wait_oks.delay(infinite_timeout=0.2) as f:
                pass

    event_loop.run_until_complete(run())
    manager.stop()

