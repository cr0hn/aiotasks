aiotasks
========

*aiotasks: A Celery like task manager for the new AsyncIO Python module*

.. image::  doc/source/_static/logo-128x128.png
    :height: 64px
    :width: 64px
    :alt: aiohttp-cache logo

.. image:: https://img.shields.io/travis/rust-lang/rust.svg
    :target: https://travis-ci.com/cr0hn/aiotasks.svg?token=pQEQN6gvxqua3sf85cs3&branch=master

.. image:: https://img.shields.io/pypi/l/Django.svg
    :target: https://github.com/cr0hn/aiotasks/blob/master/LICENSE

.. image:: https://img.shields.io/pypi/status/Django.svg
    :target: https://pypi.python.org/pypi/aiotasks/1.0.0

.. image:: https://codecov.io/gh/cr0hn/aiotasks/branch/master/graph/badge.svg?token=hPumvvJNrG
    :target: https://codecov.io/gh/cr0hn/aiotasks


+----------------+------------------------------------------------+
|Project site    | https://github.com/cr0hn/aiotasks              |
+----------------+------------------------------------------------+
|Issues          | https://github.com/cr0hn/aiotasks/issues/      |
+----------------+------------------------------------------------+
|Documentation   | https://aiotasks.readthedocs.org/              |
+----------------+------------------------------------------------+
|Author          | Daniel Garcia (cr0hn) - @ggdaniel              |
+----------------+------------------------------------------------+
|Latest Version  | 1.0.0-alpha                                    |
+----------------+------------------------------------------------+
|Python versions | 3.5 or above                                   |
+----------------+------------------------------------------------+


What's aiotasks
---------------

aiotasks is an asynchronous task queue/job queue based on distributed message passing based on Python asyncio framework. Based on the Celery Task Queue ideas, but focusing in performance, non-blocking, event-driven.

aiotasks doesn't does pulling or active waiting for tasks jobs, instead use asyncio framework to suspend the execution until any new data are received by the broker actively.

    aiotaks is still under development. Not as active as I would like (for time limitations), but the project is in active development.

    If you wan't contribute, take a look to the TODO.md file.

Usage
-----

    You can find examples at *examples* folder.

You can run aiotasks as two ways:

- Launching a aiotasks manager in an independent console / process (like Celery does), and then send any tasks to aiotasks thought the broker.
- Running the standalone way: Launching the client and the server in an unique point an running both at the same time.

Running using the manager
+++++++++++++++++++++++++

    Currently there's a limitation for launching the tasks. Python files with the tasks should be in a package to be able for aiotasks to import them.

    This limitation is in TODO to fix in the future, to allow to import .py directly without be inside in a package.

**Run the manager**

.. code-block:: bash

    > aiotasks -vvvv worker -A examples.launch_manager_tasks_and_launch_in_console

**Send the tasks**

.. code-block:: bash

    > python examples/launch_manager_tasks_and_launch_in_console.py

Running standalone
++++++++++++++++++

> python examples/standalone_tasks_standalone.py

Defining tasks
--------------

This concept was ported from Celery. Define any tasks is very simple, only need to decorate a function with *task* function.

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

Currently aiotasks only support send information using the *delay(...)* method and need to be access to the task definition:

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

Sending info to tasks & wait for response
-----------------------------------------

We can also send for a task job and wait for the response in a **non-blocking mode**:

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

Backends
--------

Currently only two backend are supported:

- Redis: redis://HOST:PORT/DB
- In memory: memory://

**Redis**

Connect to localhost and default Redis options:

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("redis://")

    ...

Custom Redis server:

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("redis://:mypassword@10.0.0.1/12")

    ...

** In memory **

This execution mode is useful to do small and local tasks. For example: If you're using aiohttp and want to send and email in a background way, you can use the standalone way and the memory backend.

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("memory://")

    ...

