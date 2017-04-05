TODO
====

New features
------------

- [X] Add a `send_tasks(..)` function
- [X] Add `current_app` var, like Flask does.
- [ ] Add actor model. A coroutine that can save the state and always are 
alive.
- [ ] Easy way to to run a list of coroutines in a pool manager. Without 
need of start the manager. Only a function like: `run_in_pool([...])`. And 
this function inherit the limits, workers, etc.
- [ ] Add ack when a messages was processed ok in an task
- [ ] Add RabbitMQ as a broker
- [ ] Add ZeroMQ as a broker
- [X] Add plugin for aiohttp
- [ ] Next task to execute
- [ ] Live reload of coroutines or hot-loading.


Improvements
------------ 

- [ ] Fix the fixture `redis_instance` to fix the correct shutdown of Redis test service
- [X] Add a warning message when use `memory://` as a backend.
- [ ] Add unsubscribe method for AsyncTaskSubscribeBase base class
- [ ] Add Cython in critical parts


Testing
------- 

- [ ] Add / fix unit testing
- [ ] Add integration tests
- [ ] Add cyclomatic complexity check
- [ ] Add Pylint test
- [X] Add flake8 test
- [ ] Add doctest
- [ ] Improve test for actions.*.console