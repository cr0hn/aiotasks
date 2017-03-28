import logging

from aiotasks import run_with_exceptions_and_logs, SharedConfig


def test_run_with_exceptions_and_logs_oks(monkeypatch):

    logger = logging.getLogger("aiotasks")

    class CustomLogger(logging.StreamHandler):
        def __init__(self):
            super(CustomLogger, self).__init__()
            self.content = []

        def emit(self, record):
            self.content.append(record.msg)

    custom = CustomLogger()
    logger.addHandler(custom)

    run_with_exceptions_and_logs(lambda x: x, 0)

    assert "Starting aioTasks" in custom.content


def test_run_with_exceptions_and_logs_exception_raised(monkeypatch):

    def raise_exception(x):
        raise Exception()

    monkeypatch.setattr(
        "aiotasks.actions.worker.console.find_manager",
        raise_exception)

    logger = logging.getLogger("aiotasks")

    class CustomLogger(logging.StreamHandler):
        def __init__(self):
            super(CustomLogger, self).__init__()
            self.content = []

        def emit(self, record):
            self.content.append(record.msg)

    custom = CustomLogger()
    logger.addHandler(custom)

    run_with_exceptions_and_logs(raise_exception, 0)

    assert "[!] Unhandled exception: " in custom.content


def test_run_with_exceptions_and_logs_ctrl_plus_c_raised(monkeypatch):

    def raise_exception(x):
        raise KeyboardInterrupt()

    monkeypatch.setattr(
        "aiotasks.actions.worker.console.find_manager",
        raise_exception)

    logger = logging.getLogger("aiotasks")

    class CustomLogger(logging.StreamHandler):
        def __init__(self):
            super(CustomLogger, self).__init__()
            self.content = []

        def emit(self, record):
            self.content.append(record.msg)

    custom = CustomLogger()
    logger.addHandler(custom)

    run_with_exceptions_and_logs(raise_exception, 1)

    assert "[*] CTRL+C caught. Exiting..." in custom.content
