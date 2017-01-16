import pytest
import asyncio

from aiotasks import build_manager, AioTasksTimeout


def test_redis_wait_oks(event_loop, redis_instance):
    
    manager = build_manager(dsn=redis_instance, loop=event_loop)

    globals()["test_redis_wait_oks_finished"] = False
    
    @manager.task()
    async def task_test_redis_wait_oks():
        return True
    
    async def run():
        manager.run()

        async with task_test_redis_wait_oks.delay() as f:
            globals()["test_redis_wait_oks_finished"] = f
        
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert globals()["test_redis_wait_oks_finished"] == True
    
    del globals()["test_redis_wait_oks_finished"]
    

def test_redis_wait_no_port_gotten(event_loop, redis_instance):
    
    _redis_instance, _ = redis_instance.rsplit(":", maxsplit=1)
    
    manager = build_manager(dsn=_redis_instance, loop=event_loop)

    globals()["test_redis_wait_no_port_gotten_finished"] = False

    @manager.task()
    async def task_test_redis_wait_no_port_gotten():
        return True

    async def run():
        manager.run()
    
        async with task_test_redis_wait_no_port_gotten.delay() as f:
            globals()["test_redis_wait_no_port_gotten_finished"] = f
    
    event_loop.run_until_complete(run())
    manager.stop()

    assert globals()["test_redis_wait_no_port_gotten_finished"] == True
    
    del globals()["test_redis_wait_no_port_gotten_finished"]


def test_redis_wait_timeout_raises(event_loop, redis_instance):
    
    manager = build_manager(dsn=redis_instance, loop=event_loop)

    globals()["test_redis_wait_timeout_raises_finished"] = False

    @manager.task()
    async def task_test_redis_wait_oks():
        await asyncio.sleep(2, loop=event_loop)
        
        return True

    async def run():
        manager.run()

        try:
            async with task_test_redis_wait_oks.delay(timeout=0.2) as f:
                pass
        except AioTasksTimeout:
                globals()["test_redis_wait_timeout_raises_finished"] = True
            
    event_loop.run_until_complete(run())
    manager.stop()

    assert globals()["test_redis_wait_timeout_raises_finished"] is True
    
    del globals()["test_redis_wait_timeout_raises_finished"]


def test_redis_wait_infinite_timeout_raises(event_loop, redis_instance):

    manager = build_manager(dsn=redis_instance, loop=event_loop)

    globals()["test_redis_wait_infinite_timeout_raises_finished"] = False

    @manager.task()
    async def task_test_redis_wait_oks():
        await asyncio.sleep(2, loop=event_loop)

        return True

    async def run():
        manager.run()
        try:
            async with task_test_redis_wait_oks.delay(infinite_timeout=0.2) as f:
                globals()["test_redis_wait_infinite_timeout_raises_finished"] = f
        except AioTasksTimeout:
            globals()["test_redis_wait_timeout_raises_finished"] = True

    event_loop.run_until_complete(run())
    manager.stop()

    assert globals()["test_redis_wait_infinite_timeout_raises_finished"] == False

    del globals()["test_redis_wait_infinite_timeout_raises_finished"]


def test_redis_wait_infinite_raises_timeout_exception(event_loop, redis_instance):

    manager = build_manager(dsn=redis_instance, loop=event_loop)

    globals()["test_redis_wait_infinite_timeout_raises_finished"] = False

    @manager.task()
    async def task_test_redis_wait_oks():
        await asyncio.sleep(2, loop=event_loop)

        return True

    async def run():
        manager.run()
        with pytest.raises(AioTasksTimeout):
            async with task_test_redis_wait_oks.delay(infinite_timeout=0.2) as f:
                pass

    event_loop.run_until_complete(run())
    manager.stop()

