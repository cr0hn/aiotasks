CHANGELOG
=========

Version 1.0.0-a2
----------------

### New features

- Add: new function **send_to** to avoid the need to has access to function to send the task to manager. Now we can use them instead of **task.delay(...)**.
- Add: new function **current_app** that will return the aiotask manager instance.
- Add: integrated cycle of deploy using Travis.

### Improvements and fixes

- Imp: the import method for tasks was changed. Now we can import tasks from a different directory or current directory.


Version 1.0.0-a1
----------------

First release