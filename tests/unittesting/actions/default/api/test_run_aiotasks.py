import pytest


from aiotasks.actions.default.api import run_default_aiotasks, \
    AioTasksDefaultModel


def test_run_default_aiotasks_runs_ok():
    AioTasksDefaultModel(application="")
    #
    # FILL THIS WITH A TEST
    #
    # assert run_default_aiotasks() is None
    pass


def test_run_default_aiotasks_empty_input():
    with pytest.raises(AssertionError):
        run_default_aiotasks(None)
