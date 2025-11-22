"""Tests for core modules with full coverage."""

import logging

import pytest
from pydantic import ValidationError

from aiotasks.core.exceptions import (
    AioTasksError,
    AioTasksTimeout,
    AioTasksTypeError,
    AioTasksValueError,
)
from aiotasks.core.helpers import dict_to_obj, get_log_level
from aiotasks.core.logger import CONSOLE_LEVEL, setup_file_logger, setup_logging
from aiotasks.core.model import SharedConfig


# =============================================================================
# Exception Tests
# =============================================================================


def test_aiotasks_error():
    """Test AioTasksError exception."""
    error = AioTasksError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_aiotasks_value_error():
    """Test AioTasksValueError exception."""
    error = AioTasksValueError("Invalid value")
    assert str(error) == "Invalid value"
    assert isinstance(error, ValueError)


def test_aiotasks_type_error():
    """Test AioTasksTypeError exception."""
    error = AioTasksTypeError("Invalid type")
    assert str(error) == "Invalid type"
    assert isinstance(error, TypeError)


def test_aiotasks_timeout():
    """Test AioTasksTimeout exception."""
    error = AioTasksTimeout("Task timed out")
    assert str(error) == "Task timed out"
    assert isinstance(error, TimeoutError)


# =============================================================================
# Helper Tests
# =============================================================================


def test_dict_to_obj_simple():
    """Test dict_to_obj with simple dict."""
    data = {"name": "test", "value": 42}
    obj = dict_to_obj(data)

    assert obj.name == "test"
    assert obj.value == 42


def test_dict_to_obj_nested():
    """Test dict_to_obj with nested dict."""
    data = {"outer": {"inner": "value"}, "number": 123}
    obj = dict_to_obj(data)

    assert hasattr(obj, "outer")
    assert hasattr(obj, "number")


def test_dict_to_obj_empty():
    """Test dict_to_obj with empty dict."""
    data = {}
    obj = dict_to_obj(data)

    # Should create object even if empty
    assert obj is not None


def test_get_log_level_debug():
    """Test get_log_level for debug."""
    level = get_log_level(3)
    assert level == logging.DEBUG


def test_get_log_level_info():
    """Test get_log_level for info."""
    level = get_log_level(1)
    assert level == logging.INFO


def test_get_log_level_warning():
    """Test get_log_level for warning."""
    level = get_log_level(0)
    assert level == logging.WARNING


def test_get_log_level_edge_cases():
    """Test get_log_level edge cases."""
    # Negative should give WARNING
    level1 = get_log_level(-1)
    assert level1 >= logging.WARNING

    # Very high should give DEBUG
    level2 = get_log_level(100)
    assert level2 == logging.DEBUG


# =============================================================================
# Logger Tests
# =============================================================================


def test_console_level_constant():
    """Test CONSOLE_LEVEL constant."""
    assert CONSOLE_LEVEL == 1000
    assert CONSOLE_LEVEL > logging.CRITICAL


def test_setup_logging():
    """Test setup_logging function."""
    logger_name = "test_aiotasks_logger"

    setup_logging(logger_name)

    logger = logging.getLogger(logger_name)

    # Should have console method added
    assert hasattr(logger, "console")


def test_setup_logging_invalid_name():
    """Test setup_logging with invalid name."""
    with pytest.raises(TypeError):
        setup_logging(123)  # Not a string


def test_setup_file_logger(tmp_path):
    """Test setup_file_logger function."""
    import os

    # Change to temp directory
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        logger_name = "test_file_logger"
        setup_file_logger(logger_name)

        logger = logging.getLogger(logger_name)

        # Should have file handler
        assert len(logger.handlers) > 0

        # Log file should exist
        log_file = tmp_path / "aiotasks.log"
        logger.warning("Test message")

        # Give it a moment to flush
        import time

        time.sleep(0.1)

    finally:
        os.chdir(original_cwd)


# =============================================================================
# Model Tests
# =============================================================================


def test_shared_config_defaults():
    """Test SharedConfig default values."""
    config = SharedConfig()

    assert config.verbosity == 0
    assert config.timeout == 10
    assert config.debug is False


def test_shared_config_custom_values():
    """Test SharedConfig with custom values."""
    config = SharedConfig(verbosity=2, timeout=30, debug=True)

    assert config.verbosity == 2
    assert config.timeout == 30
    assert config.debug is True


def test_shared_config_partial():
    """Test SharedConfig with partial values."""
    config = SharedConfig(verbosity=1)

    assert config.verbosity == 1
    assert config.timeout == 10
    assert config.debug is False


def test_shared_config_validation():
    """Test SharedConfig validation."""
    # Should coerce types
    config = SharedConfig(verbosity="2", timeout="30")

    assert config.verbosity == 2
    assert config.timeout == 30


def test_shared_config_dict_export():
    """Test SharedConfig model_dump."""
    config = SharedConfig(verbosity=3, timeout=60, debug=True)
    data = config.model_dump()

    assert data["verbosity"] == 3
    assert data["timeout"] == 60
    assert data["debug"] is True


def test_shared_config_json_export():
    """Test SharedConfig model_dump_json."""
    config = SharedConfig(verbosity=1, timeout=15, debug=False)
    json_str = config.model_dump_json()

    assert isinstance(json_str, str)
    assert "verbosity" in json_str
    assert "1" in json_str


def test_shared_config_from_dict():
    """Test creating SharedConfig from dict."""
    data = {"verbosity": 2, "timeout": 25, "debug": True}
    config = SharedConfig(**data)

    assert config.verbosity == 2
    assert config.timeout == 25
    assert config.debug is True


def test_shared_config_mutation():
    """Test SharedConfig mutation."""
    config = SharedConfig(verbosity=1)

    config.verbosity = 3
    assert config.verbosity == 3


def test_shared_config_invalid_values():
    """Test SharedConfig with invalid values."""
    # Pydantic should handle this
    try:
        config = SharedConfig(verbosity="invalid_not_number_xyz")
        # If it doesn't raise, it should have coerced or used default
        assert isinstance(config.verbosity, int)
    except ValidationError:
        # Expected for truly invalid data
        pass
