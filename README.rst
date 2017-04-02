aiotasks
========

*aiotasks: A Celery like task manager that distributes Asyncio coroutines*

.. image::  doc/source/_static/logo-128x128.png
    :height: 64px
    :width: 64px
    :alt: aiohttp-cache logo

.. image:: https://travis-ci.org/cr0hn/aiotasks.svg?branch=master
    :target: https://travis-ci.org/cr0hn/aiotasks

.. image:: https://img.shields.io/pypi/l/Django.svg
    :target: https://github.com/cr0hn/aiotasks/blob/master/LICENSE

.. image:: https://img.shields.io/pypi/status/Django.svg
    :target: https://pypi.python.org/pypi/aiotasks/1.0.0

.. image:: https://codecov.io/gh/cr0hn/aiotasks/branch/master/graph/badge.svg
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

aiotasks is an asynchronous & distributed task queue / jobs queue,
implemented as coroutines and based on Python asyncio framework.

Based on the Celery Task Queue ideas, but distributing coroutines and doing
focus in performance, non-blocking & event-driven concepts.

aiotasks doesn't pulling and doesn't has active waiting for incoming jobs,
instead use asyncio framework to suspend the execution until any new data
are received by a new broker notification.

Documentation
-------------

You can find documentation at: https://aiotasks.readthedocs.org/

Licence
-------

aiotasks is released under `BSD license <https://github
.com/cr0hn/aiotasks/blob/master/LICENSE>`_.

Contributors
------------

Contributors are welcome. You can find a list ot TODO tasks in the `TODO.md
<https://github.com/cr0hn/aiotasks/blob/master/TODO.md>`_ at the project file.

All contributors will be added to the `CONTRIBUTORS.md
<https://github.com/cr0hn/aiotasks/blob/master/CONTRIBUTORS.md>`_ file.

Thanks in advance if you're planning to contribute to the project! :)