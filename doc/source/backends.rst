Backends
========

aiotasks supports various backends. All of them are event-driven queue systems.

Currently supported backends are:

- Redis
- Memory

Planned supported in near future:

- RabbitMQ (AMQP)
- ZeroMQ

Panned supported in more long future:

- etcd
- consul

How to specify a backend
------------------------

The backends should be specified as a URI format. This is:

- BACKEND_TYPE://USER:PASSWORD@IP_OR_HOST:PORT/ANY_OTHER_INFO

Redis
-----

To configure the Redis backend we must to specify the :samp:`BACKEND_TYPE`
as **redis**, following this format: :samp:`redis://HOST:PORT/DB`

Examples
++++++++

Connect to localhost and default Redis options:

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("redis://")

    ...

Custom Redis server, with the information:

- Redis password: **mypassword**.
- Custom host: **10.0.0.1**:
- Redis database: **12**.

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("redis://:mypassword@10.0.0.1/12")

    ...

Memory
------

Memory is a special backend type. It should be used for small workload
systems or development environments.


This execution mode is useful to do small and local tasks. For example: If
you're using aiohttp and you only want to send an email in a background way,
you can use the standalone way and the memory backend.

The :samp:`BACKEND_TYPE` type is **memory** and the format is:
::samp:`memory://`.

Example
+++++++

.. code-block:: python

    from aiotasks import build_manager

    manager = build_manager("memory://")

    ...
