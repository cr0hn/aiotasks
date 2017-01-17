import time
import uuid
import asyncio

import logging
import msgpack

from aiotasks import build_manager

log = logging.getLogger("aiotasks")


# --------------------------------------------------------------------------
# Testing @task decorator
# --------------------------------------------------------------------------
def test_redis_delay_task_decorator_oks(event_loop, redis_instance):
    
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    globals()["test_redis_delay_task_decorator_oks_finished"] = False
    
    @manager.task()
    async def task_test_redis_delay_task_decorator_oks(num):
        globals()["test_redis_delay_task_decorator_oks_finished"] = True
    
    async def run():
        manager.run()
        
        await task_test_redis_delay_task_decorator_oks.delay(1)
        
        await manager.wait(timeout=0.2, exit_on_finish=True, wait_timeout=0.1)
    
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert globals()["test_redis_delay_task_decorator_oks_finished"] is True
    
    del globals()["test_redis_delay_task_decorator_oks_finished"]


def test_redis_delay_task_decorator_no_port_gotten(event_loop, redis_instance):
    
    _redis_instance, _ = redis_instance.rsplit(":", maxsplit=1)
    
    manager = build_manager(dsn=_redis_instance, loop=event_loop)
    
    globals()["test_redis_delay_task_decorator_no_port_gotten_finished"] = False
    
    @manager.task()
    async def task_test_redis_delay_task_decorator_oks_no_port_gotten(num):
        globals()["test_redis_delay_task_decorator_no_port_gotten_finished"] = True
    
    async def run():
        manager.run()
        
        await task_test_redis_delay_task_decorator_oks_no_port_gotten.delay(1)
        
        await manager.wait(timeout=0.2, exit_on_finish=True, wait_timeout=0.1)
    
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert globals()["test_redis_delay_task_decorator_no_port_gotten_finished"] is True
    
    del globals()["test_redis_delay_task_decorator_no_port_gotten_finished"]


def test_redis_delay_task_decorator_timeout_raises(event_loop, redis_instance):
    
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    globals()["test_redis_delay_task_decorator_timeout_raises_finished_tasks"] = False
    
    @manager.task()
    async def task_test_redis_delay_task_decorator_timeout_raises(num):
        await asyncio.sleep(num, loop=event_loop)
        globals()["test_redis_delay_task_decorator_timeout_raises_finished_tasks"] = True
    
    async def run():
        manager.run()
        
        await task_test_redis_delay_task_decorator_timeout_raises.delay(1)
        
        await manager.wait(timeout=0.2, exit_on_finish=True, wait_timeout=0.1)
    
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert globals()["test_redis_delay_task_decorator_timeout_raises_finished_tasks"] is False
    
    del globals()["test_redis_delay_task_decorator_timeout_raises_finished_tasks"]


def test_redis_delay_task_decorator_check_correct_timeout_reached(event_loop, redis_instance):
    
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    _start = time.time()
    
    @manager.task()
    async def task_test_redis_delay_task_decorator_check_correct_timeout_reached(num):
        pass
    
    async def run():
        manager.run()
        
        await task_test_redis_delay_task_decorator_check_correct_timeout_reached.delay(4)
        
        await manager.wait(timeout=0.5, exit_on_finish=False, wait_timeout=0.2)
    
    event_loop.run_until_complete(run())
    manager.stop()
    
    _stop = time.time()
    
    _running_time = _stop - _start
    
    assert _running_time > 0.5


def test_redis_delay_task_decorator_invalid_function(event_loop, redis_instance):
    
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
    
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    async def run():
        
        # Send an invalid task name
        task_id = uuid.uuid4().hex
        
        await manager._redis_poller.lpush(manager.task_list_name,
                                          msgpack.packb(dict(task_id=task_id,
                                                             function="non_exist",
                                                             args=(),
                                                             kwargs={})))
        
        manager.run()
        
        await manager.wait(timeout=0.2, exit_on_finish=False, wait_timeout=0.1)
    
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert "No local task with name 'non_exist'" in custom.content


def test_redis_delay_task_decorator_invalid_task_id_format(event_loop, redis_instance):
    
    import random
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
    
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    task_id = random.randint(10, 1000)
    
    @manager.task()
    async def task_test_redis_delay_task_decorator_invalid_task_id_format():
        pass
    
    async def run():
        manager.run()
        
        # Send an invalid task name
        await manager._redis_poller.lpush(manager.task_list_name,
                                          msgpack.packb(dict(task_id=task_id,
                                                             function="task_test_redis_delay_task_decorator_invalid_task_id_format",
                                                             args=(),
                                                             kwargs={})))
        
        await manager.wait(timeout=0.5, exit_on_finish=False, wait_timeout=0.1)
    
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert "Task ID '{}' has not valid UUID4 format".format(task_id) in custom.content


def test_redis_delay_task_decorator_custom_task_name(event_loop, redis_instance):
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    @manager.task(name="custom_test_redis_delay_task_decorator_custom_name")
    async def task_test_redis_delay_task_decorator_custom_name():
        pass
    
    async def run():
        manager.run()
        
        await manager.wait(timeout=0.5, exit_on_finish=False, wait_timeout=0.1)
    
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert "custom_test_redis_delay_task_decorator_custom_name" in manager.task_available_tasks.keys()


# --------------------------------------------------------------------------
# Testing add_task
# --------------------------------------------------------------------------
def test_redis_delay_add_task_oks(event_loop, redis_instance):
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    globals()["test_task_test_redis_delay_add_task_oks_finished"] = False
    
    async def task_test_redis_delay_add_task_oks(num):
        globals()["test_task_test_redis_delay_add_task_oks_finished"] = True
    
    async def run():
        manager.run()
        
        # Add task without decorator
        manager.add_task(task_test_redis_delay_add_task_oks)
        
        await task_test_redis_delay_add_task_oks.delay(1)
        
        await manager.wait(timeout=0.2, exit_on_finish=True, wait_timeout=0.1)
    
    event_loop.run_until_complete(run())
    manager.stop()
    
    assert globals()["test_task_test_redis_delay_add_task_oks_finished"] is True
    
    del globals()["test_task_test_redis_delay_add_task_oks_finished"]


def test_redis_delay_add_task_custom_task_name(event_loop, redis_instance):
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    async def task_test_redis_delay_add_task_custom_task_name():
        pass
    
    async def run():
        manager.run()
        
        # Add task without decorator
        manager.add_task(task_test_redis_delay_add_task_custom_task_name,
                         name="custom_task_test_redis_delay_task_decorator_oks")
        
        await task_test_redis_delay_add_task_custom_task_name.delay()
        
        await manager.wait(timeout=0.2, exit_on_finish=True, wait_timeout=0.1)
    
    event_loop.run_until_complete(run())
    manager.stop()

    assert "custom_task_test_redis_delay_task_decorator_oks" in manager.task_available_tasks.keys()


def test_redis_delay_add_task_non_coroutine_as_input(event_loop, redis_instance):
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
    
    manager = build_manager(dsn=redis_instance, loop=event_loop)
    
    def task_test_redis_delay_add_task_non_coroutine_as_input():
        pass
    
    async def run():
        manager.run()
        
        # Add task without decorator
        manager.add_task(task_test_redis_delay_add_task_non_coroutine_as_input,
                         name="custom_task_test_redis_delay_task_decorator_oks")
        
    event_loop.run_until_complete(run())
    manager.stop()

    assert "Function 'task_test_redis_delay_add_task_non_coroutine_as_input' is not a coroutine and can't be added as a task" in custom.content

    # assert "custom_task_test_redis_delay_task_decorator_oks" in manager._tasks.keys()
