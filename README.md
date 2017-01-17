aiotasks
========

![Logo](doc/source/_static/logo.jpg)

*aiotasks: A Celery like task manager for the new AsyncIO Python module*

Code | https://github.com/cr0hn/aiotasks
---- | ----------------------------------------------
Issues | https://github.com/cr0hn/aiotasks/issues/
Python version | Python 3.5 and above

What's aiotasks
---------------

aiotasks is an asynchronous task queue/job queue based on distributed message passing based on Python asyncio framework. Based on the Celery Task Queue ideas, but focusing in performance, non-blocking, event-driven.

What's new?
-----------

This aiotasks version, add a lot of new features and fixes, like:

Version 1.0.0
+++++++++++++

- First version released

You can read entire list in CHANGELOG file.

Installation
------------

Simple
++++++

Install aiotasks is so easy:

```
$ python3.5 -m pip install aiotasks
```

With extra performance
++++++++++++++++++++++

Aiotasks also includes some optional dependencies to add extra performance but requires a bit different installation, because they (usually) depends of C extensions.

To install the tool with extra performance you must do:

```
$ python3.5 -m pip install 'aiotasks[performance]'
```

**Remember that aiotasks only runs in Python 3.5 and above**.

Quick start
-----------

You can display inline help writing:

From cloned project
+++++++++++++++++++

```bash

python aiotasks.py -h
```

From pip installation
+++++++++++++++++++++

```bash

aiotasks -h
```