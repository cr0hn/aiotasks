Welcome to aiotasks's documentation!
====================================

+----------------+------------------------------------+
|Project site    | http://github.com/cr0hn/aiotasks   |
+----------------+------------------------------------+
|Author          | Daniel Garcia (cr0hn) - @ggdaniel  |
+----------------+------------------------------------+
|Documentation   | http://aiotasks.readthedocs.org    |
+----------------+------------------------------------+
|Last Version    | 1.0.0                              |
+----------------+------------------------------------+
|Python versions | 3.5 or above                       |
+----------------+------------------------------------+

*aiotasks: A Celery like task manager that distributes Asyncio coroutines*

What's aiotasks
---------------

aiotasks is an asynchronous & distributed task queue / jobs queue,
implemented as coroutines and based on Python asyncio framework.

Based on the Celery Task Queue ideas, but distributing coroutines and doing
focus in performance, non-blocking & event-driven concepts.

aiotasks doesn't pulling and doesn't has active waiting for incoming jobs,
instead use asyncio framework to suspend the execution until any new data
are received by a new broker notification.

.. note::

    aiotaks is still under development. Not as active as I would like (for
    time limitations), but the project is in active development.

    If you wan't contribute, take a look to the TODO.md file.

Contents
--------

.. toctree::
   :maxdepth: 2

   install
   quickstart
   backends
   architecture
   contributors
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

