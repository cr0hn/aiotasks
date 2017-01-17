TODO
====

New features
------------

- [ ] Add a `send_tasks(..)` function
- [ ] Add `redis_instance=...` parameter for the `.delay(...)` methods.

Improvements
------------ 

- [ ] Fix the fixture `redis_instance` to fix the correct shutdown of Redis test service
- [ ] Add a warning message when use `memory://` as a backend.


Testing
------- 

- [ ] Add cyclomatic complexity check
- [ ] Add Pylint test
- [X] Add flake8 test
- [ ] Add doctest
