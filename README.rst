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

.. image:: https://readthedocs.org/projects/aiotasks/badge/?version=latest
    :target: http://aiotasks.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

+----------------+------------------------------------------------+
|Project site    | https://github.com/cr0hn/aiotasks              |
+----------------+------------------------------------------------+
|Issues          | https://github.com/cr0hn/aiotasks/issues/      |
+----------------+------------------------------------------------+
|Documentation   | http://aiotasks.readthedocs.io                 |
+----------------+------------------------------------------------+
|Author          | Daniel Garcia (cr0hn) - @ggdaniel              |
+----------------+------------------------------------------------+
|Latest Version  | 1.0.0-alpha                                    |
+----------------+------------------------------------------------+
|Python versions | 3.5 or above                                   |
+----------------+------------------------------------------------+


What's aiotasks
---------------

aiotasks is an asynchronous & distributed task/jobs queue,
implemented as coroutines and based on Python asyncio framework.

Based on the Celery Task Queue ideas, but distributing coroutines and focusing
on performance, non-blocking, & event-driven concepts.

aiotasks does not pull and does not actively wait for incoming jobs.
Instead it uses asyncio framework to suspend the execution until any new data
is received by a new broker notification.

Documentation
-------------

You can find documentation at: https://aiotasks.readthedocs.org/

Licence
-------

aiotasks is released under `BSD license <https://github
.com/cr0hn/aiotasks/blob/master/LICENSE>`_.

Contributors
------------

Contributors are welcome. You can find a list of TODO tasks in the `TODO.md
<https://github.com/cr0hn/aiotasks/blob/master/TODO.md>`_ at the project file.

All contributors will be added to the `CONTRIBUTORS.md
<https://github.com/cr0hn/aiotasks/blob/master/CONTRIBUTORS.md>`_ file.

Thanks in advance if you're planning to contribute to the project! :)
