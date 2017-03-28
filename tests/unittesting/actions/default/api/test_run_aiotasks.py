import pytest


from aiotasks.actions import find_manager, \
    AioTasksDefaultModel


def test_run_default_aiotasks_runs_ok():
    AioTasksDefaultModel(application="")
    #
    # FILL THIS WITH A TEST
    #
    # assert find_manager() is None
    pass


def test_run_default_aiotasks_empty_input():
    with pytest.raises(AssertionError):
        find_manager(None)
