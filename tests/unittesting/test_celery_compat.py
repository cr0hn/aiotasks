"""Tests for Celery Protocol v2 compatibility module.

This test suite verifies the complete Celery interoperability implementation,
ensuring AioTasks can send and receive messages in Celery Protocol v2 format.
"""

import json
import uuid

import pytest

try:
    import umsgpack as msgpack
except ImportError:
    import msgpack

from aiotasks.celery_compat import (
    decode_celery_task,
    deserialize_celery_message,
    encode_celery_task,
    generate_task_id,
    get_hostname,
    is_celery_message,
    serialize_celery_message,
)


class TestCeleryProtocolSerialization:
    """Test Celery Protocol v2 message serialization."""

    def test_serialize_basic_task(self):
        """Test serializing a basic task with args and kwargs."""
        task_name = "tasks.add"
        args = [4, 5]
        kwargs = {"debug": True}
        task_id = "test-task-id-123"

        properties, headers, body = serialize_celery_message(
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            task_id=task_id,
        )

        # Verify properties
        assert properties["correlation_id"] == task_id
        assert properties["content_type"] == "application/json"
        assert properties["content_encoding"] == "utf-8"
        assert properties["delivery_mode"] == 2  # Persistent

        # Verify headers
        assert headers["lang"] == "py"
        assert headers["task"] == task_name
        assert headers["id"] == task_id
        assert headers["root_id"] == task_id
        assert headers["retries"] == 0
        assert headers["argsrepr"] == repr(args)
        assert headers["kwargsrepr"] == repr(kwargs)

        # Verify body
        assert body["args"] == args
        assert body["kwargs"] == kwargs
        assert "embed" in body

    def test_serialize_with_eta(self):
        """Test serializing task with ETA."""
        eta = "2024-12-31T23:59:59"
        properties, headers, body = serialize_celery_message(
            task_name="tasks.delayed",
            eta=eta,
        )

        assert headers["eta"] == eta

    def test_serialize_with_expires(self):
        """Test serializing task with expiration."""
        expires = "2024-12-31T23:59:59"
        properties, headers, body = serialize_celery_message(
            task_name="tasks.expiring",
            expires=expires,
        )

        assert headers["expires"] == expires

    def test_serialize_with_timelimit(self):
        """Test serializing task with time limit."""
        timelimit = (30, 60)  # soft, hard
        properties, headers, body = serialize_celery_message(
            task_name="tasks.limited",
            timelimit=timelimit,
        )

        assert headers["timelimit"] == timelimit

    def test_serialize_with_retries(self):
        """Test serializing task with retry count."""
        properties, headers, body = serialize_celery_message(
            task_name="tasks.retry",
            retries=3,
        )

        assert headers["retries"] == 3

    def test_serialize_auto_generates_task_id(self):
        """Test that task_id is auto-generated if not provided."""
        properties, headers, body = serialize_celery_message(
            task_name="tasks.test",
        )

        task_id = properties["correlation_id"]
        assert task_id is not None
        assert len(task_id) == 36  # UUID4 format
        # Verify it's a valid UUID
        uuid.UUID(task_id, version=4)

    def test_serialize_msgpack_format(self):
        """Test serializing with msgpack format."""
        properties, headers, body = serialize_celery_message(
            task_name="tasks.test",
            serializer="msgpack",
        )

        assert properties["content_type"] == "application/x-msgpack"


class TestCeleryProtocolDeserialization:
    """Test Celery Protocol v2 message deserialization."""

    def test_deserialize_basic_message(self):
        """Test deserializing a basic Celery message."""
        task_id = "test-id-123"
        task_name = "tasks.add"
        args = [4, 5]
        kwargs = {"debug": True}

        properties = {
            "correlation_id": task_id,
            "content_type": "application/json",
        }
        headers = {
            "id": task_id,
            "task": task_name,
            "retries": 0,
        }
        body = {
            "args": args,
            "kwargs": kwargs,
        }

        result = deserialize_celery_message(properties, headers, body)

        assert result["task_id"] == task_id
        assert result["task_name"] == task_name
        assert result["args"] == args
        assert result["kwargs"] == kwargs
        assert result["retries"] == 0

    def test_deserialize_with_metadata(self):
        """Test deserializing message with full metadata."""
        eta = "2024-12-31T23:59:59"
        origin = "worker@hostname"
        root_id = "root-123"

        properties = {"correlation_id": "task-123"}
        headers = {
            "id": "task-123",
            "task": "tasks.test",
            "eta": eta,
            "origin": origin,
            "root_id": root_id,
        }
        body = {"args": [], "kwargs": {}}

        result = deserialize_celery_message(properties, headers, body)

        assert result["eta"] == eta
        assert result["origin"] == origin
        assert result["root_id"] == root_id

    def test_deserialize_with_callbacks(self):
        """Test deserializing message with callbacks/errbacks."""
        properties = {"correlation_id": "task-123"}
        headers = {"id": "task-123", "task": "tasks.test"}
        body = {
            "args": [],
            "kwargs": {},
            "embed": {
                "callbacks": ["tasks.on_success"],
                "errbacks": ["tasks.on_error"],
                "chain": ["tasks.next"],
                "chord": None,
            },
        }

        result = deserialize_celery_message(properties, headers, body)

        assert result["callbacks"] == ["tasks.on_success"]
        assert result["errbacks"] == ["tasks.on_error"]
        assert result["chain"] == ["tasks.next"]


class TestCeleryTaskEncoding:
    """Test complete Celery task encoding."""

    def test_encode_json_format(self):
        """Test encoding task in JSON format."""
        task_name = "tasks.add"
        args = [4, 5]
        kwargs = {"debug": True}

        encoded = encode_celery_task(
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            serializer="json",
        )

        # Verify it's valid JSON
        decoded = json.loads(encoded.decode("utf-8"))

        assert "properties" in decoded
        assert "headers" in decoded
        assert "body" in decoded
        assert decoded["headers"]["task"] == task_name
        assert decoded["body"]["args"] == args
        assert decoded["body"]["kwargs"] == kwargs

    def test_encode_msgpack_format(self):
        """Test encoding task in msgpack format."""
        task_name = "tasks.multiply"
        args = [3, 7]

        encoded = encode_celery_task(
            task_name=task_name,
            args=args,
            serializer="msgpack",
        )

        # Verify it's valid msgpack
        decoded = msgpack.unpackb(encoded, raw=False)

        assert "properties" in decoded
        assert "headers" in decoded
        assert "body" in decoded
        assert decoded["headers"]["task"] == task_name

    def test_encode_with_custom_task_id(self):
        """Test encoding with custom task ID."""
        custom_id = "custom-uuid-123"
        encoded = encode_celery_task(
            task_name="tasks.test",
            task_id=custom_id,
        )

        decoded = json.loads(encoded.decode("utf-8"))
        assert decoded["properties"]["correlation_id"] == custom_id
        assert decoded["headers"]["id"] == custom_id


class TestCeleryTaskDecoding:
    """Test complete Celery task decoding."""

    def test_decode_json_message(self):
        """Test decoding JSON-encoded Celery message."""
        # Create a Celery message
        task_name = "tasks.divide"
        args = [10, 2]
        encoded = encode_celery_task(task_name=task_name, args=args, serializer="json")

        # Decode it
        result = decode_celery_task(encoded, serializer="json")

        assert result["task_name"] == task_name
        assert result["args"] == args

    def test_decode_msgpack_message(self):
        """Test decoding msgpack-encoded Celery message."""
        task_name = "tasks.power"
        args = [2, 8]
        encoded = encode_celery_task(task_name=task_name, args=args, serializer="msgpack")

        result = decode_celery_task(encoded, serializer="msgpack")

        assert result["task_name"] == task_name
        assert result["args"] == args

    def test_round_trip_json(self):
        """Test encode/decode round-trip with JSON."""
        original_data = {
            "task_name": "tasks.complex",
            "args": [1, 2, 3],
            "kwargs": {"multiply": True, "factor": 2.5},
        }

        encoded = encode_celery_task(**original_data, serializer="json")
        decoded = decode_celery_task(encoded, serializer="json")

        assert decoded["task_name"] == original_data["task_name"]
        assert decoded["args"] == original_data["args"]
        assert decoded["kwargs"] == original_data["kwargs"]

    def test_round_trip_msgpack(self):
        """Test encode/decode round-trip with msgpack."""
        original_data = {
            "task_name": "tasks.data_processing",
            "args": ["input.csv"],
            "kwargs": {"delimiter": ",", "header": True},
        }

        encoded = encode_celery_task(**original_data, serializer="msgpack")
        decoded = decode_celery_task(encoded, serializer="msgpack")

        assert decoded["task_name"] == original_data["task_name"]
        assert decoded["args"] == original_data["args"]
        assert decoded["kwargs"] == original_data["kwargs"]


class TestCeleryMessageDetection:
    """Test Celery message format detection."""

    def test_detect_celery_json_message(self):
        """Test detecting Celery JSON message."""
        encoded = encode_celery_task(task_name="tasks.test", serializer="json")
        assert is_celery_message(encoded) is True

    def test_detect_celery_msgpack_message(self):
        """Test detecting Celery msgpack message."""
        encoded = encode_celery_task(task_name="tasks.test", serializer="msgpack")
        # Msgpack messages should also be detectable
        assert is_celery_message(encoded) is True

    def test_detect_aiotasks_message(self):
        """Test detecting non-Celery message (AioTasks format)."""
        # AioTasks native format
        aiotasks_msg = msgpack.packb(
            {
                "task_id": "123",
                "function": "tasks.test",
                "args": [],
                "kwargs": {},
            },
            use_bin_type=True,
        )
        assert is_celery_message(aiotasks_msg) is False

    def test_detect_invalid_message(self):
        """Test detecting invalid message."""
        invalid_msg = b"not a valid message"
        assert is_celery_message(invalid_msg) is False

    def test_detect_from_dict(self):
        """Test detecting Celery message from dict."""
        celery_dict = {
            "properties": {"correlation_id": "123"},
            "headers": {"task": "tasks.test", "id": "123"},
            "body": {"args": [], "kwargs": {}},
        }
        assert is_celery_message(celery_dict) is True

        aiotasks_dict = {
            "task_id": "123",
            "function": "tasks.test",
            "args": [],
            "kwargs": {},
        }
        assert is_celery_message(aiotasks_dict) is False


class TestHelperFunctions:
    """Test helper utility functions."""

    def test_generate_task_id(self):
        """Test task ID generation."""
        task_id = generate_task_id()
        assert isinstance(task_id, str)
        assert len(task_id) == 36  # UUID4 format
        # Verify it's a valid UUID
        uuid.UUID(task_id, version=4)

    def test_generate_unique_ids(self):
        """Test that generated IDs are unique."""
        ids = {generate_task_id() for _ in range(100)}
        assert len(ids) == 100  # All unique

    def test_get_hostname(self):
        """Test hostname retrieval."""
        hostname = get_hostname()
        assert isinstance(hostname, str)
        assert len(hostname) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_serialize_empty_args_kwargs(self):
        """Test serializing with empty args and kwargs."""
        properties, headers, body = serialize_celery_message(
            task_name="tasks.noargs",
            args=None,
            kwargs=None,
        )

        assert body["args"] == []
        assert body["kwargs"] == {}

    def test_serialize_tuple_args(self):
        """Test serializing with tuple args (should convert to list)."""
        args = (1, 2, 3)
        properties, headers, body = serialize_celery_message(
            task_name="tasks.test",
            args=args,
        )

        # Celery expects lists, not tuples
        assert isinstance(body["args"], list)
        assert body["args"] == [1, 2, 3]

    def test_serialize_complex_kwargs(self):
        """Test serializing with complex kwargs."""
        kwargs = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "string": "test",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
        }
        properties, headers, body = serialize_celery_message(
            task_name="tasks.complex",
            kwargs=kwargs,
        )

        assert body["kwargs"] == kwargs

    def test_deserialize_missing_fields(self):
        """Test deserializing with missing optional fields."""
        properties = {"correlation_id": "123"}
        headers = {"id": "123", "task": "tasks.test"}
        body = {"args": [], "kwargs": {}}

        result = deserialize_celery_message(properties, headers, body)

        # Should handle missing fields gracefully
        assert result["task_id"] == "123"
        assert result["task_name"] == "tasks.test"
        assert result["eta"] is None
        assert result["expires"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
