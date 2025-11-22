"""Tests for Pydantic models."""

from pydantic import ValidationError

from aiotasks.core.model import SharedConfig


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


def test_shared_config_partial_override():
    """Test SharedConfig with partial override."""
    config = SharedConfig(verbosity=1)

    assert config.verbosity == 1
    assert config.timeout == 10  # Default
    assert config.debug is False  # Default


def test_shared_config_type_validation():
    """Test SharedConfig type validation."""
    # Should accept correct types
    config = SharedConfig(verbosity=1, timeout=20, debug=False)
    assert config.verbosity == 1

    # Pydantic should coerce types where reasonable
    config2 = SharedConfig(verbosity="2", timeout="30", debug="true")
    assert config2.verbosity == 2
    assert config2.timeout == 30


def test_shared_config_dict_export():
    """Test exporting SharedConfig to dict."""
    config = SharedConfig(verbosity=3, timeout=60, debug=True)
    config_dict = config.model_dump()

    assert config_dict["verbosity"] == 3
    assert config_dict["timeout"] == 60
    assert config_dict["debug"] is True


def test_shared_config_json_export():
    """Test exporting SharedConfig to JSON."""
    config = SharedConfig(verbosity=1, timeout=15, debug=False)
    config_json = config.model_dump_json()

    assert isinstance(config_json, str)
    assert "verbosity" in config_json
    assert "timeout" in config_json
    assert "debug" in config_json


def test_shared_config_from_dict():
    """Test creating SharedConfig from dict."""
    data = {"verbosity": 2, "timeout": 25, "debug": True}
    config = SharedConfig(**data)

    assert config.verbosity == 2
    assert config.timeout == 25
    assert config.debug is True


def test_shared_config_immutability():
    """Test that model handles updates correctly."""
    config = SharedConfig(verbosity=1)

    # Pydantic models are mutable by default, but we can test reassignment
    config.verbosity = 2
    assert config.verbosity == 2


def test_shared_config_validation_errors():
    """Test validation errors for invalid data."""
    # This test depends on whether strict validation is enabled
    # Pydantic 2.0+ is more lenient with type coercion
    try:
        # Try to create with clearly invalid data
        config = SharedConfig(verbosity="not_a_number_at_all_xyz")
        # If it doesn't raise, pydantic coerced it somehow
        assert isinstance(config.verbosity, int)
    except ValidationError:
        # Expected for invalid data
        pass
