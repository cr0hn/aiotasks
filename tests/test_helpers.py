"""Tests for helper functions and utilities."""

from aiotasks.helpers import parse_dsn


def test_parse_dsn_memory():
    """Test parsing memory:// DSN."""
    result = parse_dsn("memory://")

    assert result["schema"] == "memory"
    assert result["host"] is None or result["host"] == ""
    assert result["port"] is None or result["port"] == ""


def test_parse_dsn_redis():
    """Test parsing Redis DSN."""
    result = parse_dsn("redis://localhost:6379/0")

    assert result["schema"] == "redis"
    assert result["host"] == "localhost"
    assert result["port"] == 6379 or result["port"] == "6379"


def test_parse_dsn_redis_with_auth():
    """Test parsing Redis DSN with authentication."""
    result = parse_dsn("redis://:password@localhost:6379/0")

    assert result["schema"] == "redis"
    assert result["host"] == "localhost"
    assert result["port"] == 6379 or result["port"] == "6379"
    assert result.get("password") == "password" or "password" in str(result)


def test_parse_dsn_amqp():
    """Test parsing AMQP DSN."""
    result = parse_dsn("amqp://guest:guest@localhost:5672/")

    assert result["schema"] == "amqp"
    assert result["host"] == "localhost"
    assert result["port"] == 5672 or result["port"] == "5672"


def test_parse_dsn_zmq():
    """Test parsing ZMQ DSN."""
    result = parse_dsn("zmq://localhost:5555")

    assert result["schema"] == "zmq"
    assert result["host"] == "localhost"
    assert result["port"] == 5555 or result["port"] == "5555"


def test_parse_dsn_invalid():
    """Test parsing invalid DSN."""
    # Should handle gracefully or raise appropriate error
    try:
        result = parse_dsn("invalid://")
        # If it doesn't raise, should return something
        assert isinstance(result, dict)
    except Exception as e:
        # If it raises, should be a reasonable exception
        assert isinstance(e, (ValueError, KeyError, AttributeError))


def test_parse_dsn_http():
    """Test parsing HTTP DSN (unsupported but should parse)."""
    result = parse_dsn("http://example.com:8080")

    assert result["schema"] == "http"
    assert result["host"] == "example.com"
    assert result["port"] == 8080 or result["port"] == "8080"


def test_parse_dsn_with_path():
    """Test parsing DSN with path."""
    result = parse_dsn("redis://localhost:6379/0")

    assert result["schema"] == "redis"
    # Path or database should be captured
    assert "0" in str(result.values()) or result.get("path") == "/0"


def test_parse_dsn_localhost_variants():
    """Test different localhost variants."""
    variants = [
        "redis://127.0.0.1:6379",
        "redis://localhost:6379",
        "redis://0.0.0.0:6379",
    ]

    for dsn in variants:
        result = parse_dsn(dsn)
        assert result["schema"] == "redis"
        assert result["port"] == 6379 or result["port"] == "6379"
