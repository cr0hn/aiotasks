Quick Start
===========

This is a quick start with aiotasks with the minimum information to start.

.. note::

    You can find examples at project :samp:`examples` folder.

Running modes
-------------

You can run aiotasks as two ways:

- Launching an aiotasks manager in an independent console / process (like
  Celery does), and then sending any tasks to aiotasks through the broker.
- Running the standalone way: Launching the client and the server in a
  unique point and running both at the same time.

Running using the manager
-------------------------

Run the manager
+++++++++++++++

.. code-block:: bash

    > aiotasks -vvvv worker -A examples.launch_manager_tasks_and_launch_in_console

Send the tasks
++++++++++++++

.. code-block:: bash

    > python examples/launch_manager_tasks_and_launch_in_console.py

Running standalone
------------------

.. code-block:: bash

    > python examples/standalone_tasks_standalone.py

Defining tasks
--------------

This concept was ported from Celery. Defining any tasks is very simple, only
need to decorate a function with *task* function.

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("redis://")

    @manager.task()  # <-- DEFINITION OF TASK
    async def task_01(num):  # <-- TASK SHOULD BE A **COROUTINE**
        print("Task 01 starting: {}".format(num))
        await asyncio.sleep(2, loop=manager.loop)
        print("Task 01 stopping")


Sending info to tasks
---------------------

We can send tasks to the manager using methods:

Using *delay* method
++++++++++++++++++++

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("redis://")

    @manager.task()
    async def task_01(num):
        await asyncio.sleep(0, loop=manager.loop)

    async def generate_tasks():
        # Generates 5 tasks
        for x in range(5):
            await task_01.delay(x)  # <-- METHOD DELAY SEND A TASK

    if __name__ == '__main__':
        manager.loop.run_until_complete(generate_tasks())

Using *send_task*
+++++++++++++++++

.. code-block:: python

    from aiotasks import build_manager, send_task

    manager = build_manager("redis://")

    @manager.task()
    async def task_01(num):
        await asyncio.sleep(0, loop=manager.loop)

    async def generate_tasks():
        # Generates 5 tasks
        for x in range(5):
            await send_task("task_01", args=(x, ))  # <-- SENDING A TASK

    if __name__ == '__main__':
        manager.loop.run_until_complete(generate_tasks())

Sending info to tasks & wait for response
-----------------------------------------

We can also send for a task job and wait for the response in a
**non-blocking mode**:

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("redis://")

    @manager.task()
    async def task_01(num):
        await asyncio.sleep(0, loop=manager.loop)

    async def generate_tasks():
        # Generates 5 tasks
        async with task_01.wait(x) as f:  # <-- NON-BLOCKING WAITING FOR RESPONSE
            print(f)

    if __name__ == '__main__':
        manager.loop.run_until_complete(generate_tasks())
