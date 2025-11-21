import logging

import pytest
from booby.errors import FieldError

from aiotasks.actions import launch_aiotasks_worker_in_console


def test_launch_aiotasks_worker_in_console_oks(monkeypatch):
    logger = logging.getLogger("aiotasks")

    class CustomLogger(logging.StreamHandler):
        def __init__(self):
            super(CustomLogger, self).__init__()
            self.content = []

        def emit(self, record):
            self.content.append(record.msg)

    custom = CustomLogger()
    logger.addHandler(custom)

    monkeypatch.setattr(
        "aiotasks.actions.worker.console.find_manager",
        lambda x: "OK")

    launch_aiotasks_worker_in_console(dict(), **dict())
    assert "Starting aioTasks" in custom.content
    assert "[*] Shutdown..." in custom.content


def test_launch_aiotasks_worker_in_console_config_params_not_valid():
    logger = logging.getLogger("aiotasks")

    class CustomLogger(logging.StreamHandler):
        def __init__(self):
            super(CustomLogger, self).__init__()
            self.content = []

        def emit(self, record):
            self.content.append(record.msg)

    custom = CustomLogger()
    logger.addHandler(custom)

    with pytest.raises(FieldError):
        launch_aiotasks_worker_in_console(dict(one="two"), **dict())


def test_launch_aiotasks_worker_in_console_invalid_config_values():
    logger = logging.getLogger("aiotasks")

    class CustomLogger(logging.StreamHandler):
        def __init__(self):
            super(CustomLogger, self).__init__()
            self.content = []

        def emit(self, record):
            self.content.append(record.msg)

    custom = CustomLogger()
    logger.addHandler(custom)

    launch_aiotasks_worker_in_console(dict(application=1), **dict())

    assert "'application' property should be a string" in custom.content
