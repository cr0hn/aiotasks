# from aiotasks import build_manager
#
#
# def test_redis_decorated_functions_has_correct_dynamic_functions(event_loop, redis_instance):
#     manager = build_manager(dsn=redis_instance, loop=event_loop)
#
#     globals()["has_delay_method"] = False
#     globals()["has_wait_method"] = False
#     globals()["has_subscribe_method"] = False
#
#     @manager.task()
#     async def task_test_redis_decorated_functions_has_correct_dynamic_functions():
#         pass
#
#     async def run():
#         manager.run()
#
#         globals()["has_delay_method"] = hasattr(task_test_redis_decorated_functions_has_correct_dynamic_functions,
#                                                 "delay")
#
#         await manager.wait(timeout=0.5, exit_on_finish=True, wait_timeout=0.2)
#
#     event_loop.run_until_complete(run())
#     manager.stop()
#
#     assert globals()["has_delay_method"] is True
#
#     del globals()["has_delay_method"]
#
