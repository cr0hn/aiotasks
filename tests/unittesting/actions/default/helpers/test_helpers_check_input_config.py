import pytest

from aiotasks import check_input_config, SharedConfig, AioTasksTypeError


def test_check_input_config_return_none():
    assert check_input_config(SharedConfig()) is None


def test_check_input_config_input_none():
    assert check_input_config(None) is None


def test_check_input_config_raise_exception():
    with pytest.raises(AioTasksTypeError):
        check_input_config(SharedConfig(verbosity="2"))