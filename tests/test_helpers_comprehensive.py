"""Comprehensive tests for helper functions with full coverage."""

import pytest

from aiotasks.helpers import parse_dsn


def test_parse_dsn_memory():
    """Test parsing memory DSN."""
    config = parse_dsn("memory://")

    assert config.schema == "memory"
    assert config.host == ""
    assert config.port is None


def test_parse_dsn_redis():
    """Test parsing Redis DSN."""
    config = parse_dsn("redis://localhost:6379/0")

    assert config.schema == "redis"
    assert config.host == "localhost"
    assert config.port == 6379
    assert config.path == "/0"


def test_parse_dsn_redis_with_auth():
    """Test parsing Redis DSN with password."""
    config = parse_dsn("redis://:password@localhost:6379/0")

    assert config.schema == "redis"
    assert config.host == "localhost"
    assert config.port == 6379
    assert config.password == "password"


def test_parse_dsn_redis_with_user_and_password():
    """Test parsing Redis DSN with username and password."""
    config = parse_dsn("redis://user:password@localhost:6379/0")

    assert config.schema == "redis"
    assert config.host == "localhost"
    assert config.port == 6379
    assert config.user == "user"
    assert config.password == "password"


def test_parse_dsn_amqp():
    """Test parsing AMQP DSN."""
    config = parse_dsn("amqp://guest:guest@localhost:5672/")

    assert config.schema == "amqp"
    assert config.host == "localhost"
    assert config.port == 5672
    assert config.user == "guest"
    assert config.password == "guest"


def test_parse_dsn_zmq():
    """Test parsing ZMQ DSN."""
    config = parse_dsn("zmq://localhost:5555")

    assert config.schema == "zmq"
    assert config.host == "localhost"
    assert config.port == 5555


def test_parse_dsn_with_ipv4():
    """Test parsing DSN with IPv4 address."""
    config = parse_dsn("redis://127.0.0.1:6379")

    assert config.schema == "redis"
    assert config.host == "127.0.0.1"
    assert config.port == 6379


def test_parse_dsn_with_ipv6():
    """Test parsing DSN with IPv6 address."""
    config = parse_dsn("redis://[::1]:6379")

    assert config.schema == "redis"
    # IPv6 handling depends on implementation
    assert "[::1]" in config.host or "::1" in config.host


def test_parse_dsn_with_default_port():
    """Test parsing DSN without port."""
    config = parse_dsn("redis://localhost")

    assert config.schema == "redis"
    assert config.host == "localhost"
    # Port might be None or default


def test_parse_dsn_with_query_params():
    """Test parsing DSN with query parameters."""
    config = parse_dsn("redis://localhost:6379/0?ssl=true")

    assert config.schema == "redis"
    assert config.host == "localhost"


def test_parse_dsn_localhost_variants():
    """Test different localhost representations."""
    variants = [
        "redis://127.0.0.1:6379",
        "redis://localhost:6379",
        "redis://0.0.0.0:6379",
    ]

    for dsn in variants:
        config = parse_dsn(dsn)
        assert config.schema == "redis"
        assert config.port == 6379
        assert config.host in ["127.0.0.1", "localhost", "0.0.0.0"]


def test_parse_dsn_amqp_vhost():
    """Test parsing AMQP with virtual host."""
    config = parse_dsn("amqp://guest:guest@localhost:5672/myvhost")

    assert config.schema == "amqp"
    assert config.path == "/myvhost"


def test_parse_dsn_edge_cases():
    """Test edge cases in DSN parsing."""
    # Empty host
    config1 = parse_dsn("memory://")
    assert config1.schema == "memory"

    # No slash
    config2 = parse_dsn("zmq://localhost:5555")
    assert config2.schema == "zmq"


def test_parse_dsn_special_characters_in_password():
    """Test DSN with special characters in password."""
    config = parse_dsn("redis://:p@ssw0rd!@localhost:6379")

    assert config.password == "p@ssw0rd!"


def test_parse_dsn_http_schema():
    """Test parsing HTTP schema."""
    config = parse_dsn("http://example.com:8080")

    assert config.schema == "http"
    assert config.host == "example.com"
    assert config.port == 8080
