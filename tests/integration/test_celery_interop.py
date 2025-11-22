"""Integration tests for Celery Protocol v2 interoperability.

These tests verify that AioTasks can send and receive messages compatible
with Celery workers, enabling mixed deployments and gradual migration.
"""

import json
import uuid

import pytest

try:
    import umsgpack as msgpack
except ImportError:
    import msgpack

from aiotasks import AioTasks
from aiotasks.celery_compat import decode_celery_task, is_celery_message


@pytest.mark.asyncio()
class TestCeleryInteroperability:
    """Test interoperability between AioTasks and Celery."""

    async def test_aiotasks_sends_celery_format(self):
        """Test that AioTasks with celery_compat=True sends Celery-format messages."""
        app = AioTasks(
            name="test_celery_app",
            broker="memory://",
            celery_compat=True,
        )

        # Register a test task
        @app.task()
        async def add(x: int, y: int) -> int:
            """Test task that adds two numbers."""
            return x + y

        # Build a delay message
        delay_ctx = add.delay(4, 5)
        message = delay_ctx.build_delay_message()

        # Verify it's in Celery format
        assert is_celery_message(message) is True

        # Decode and verify content
        decoded = decode_celery_task(message, serializer="json")
        assert decoded["task_name"] == "add"
        assert decoded["args"] == [4, 5]
        assert "task_id" in decoded

    async def test_celery_compat_disabled_uses_native_format(self):
        """Test that celery_compat=False uses AioTasks native format."""
        app = AioTasks(
            name="test_native",
            broker="memory://",
            celery_compat=False,  # Explicitly disable
        )

        @app.task()
        async def subtract(x: int, y: int) -> int:
            """Test task."""
            return x - y

        # Build message
        delay_ctx = subtract.delay(10, 3)
        message = delay_ctx.build_delay_message()

        # Should NOT be Celery format
        assert is_celery_message(message) is False

        # Should be msgpack AioTasks format
        decoded = msgpack.unpackb(message, raw=False)
        assert "function" in decoded
        assert "task_id" in decoded
        assert decoded["function"] == "subtract"
        assert decoded["args"] == [10, 3]

    async def test_celery_message_metadata(self):
        """Test that Celery messages include proper metadata."""
        app = AioTasks(
            name="test_metadata",
            broker="memory://",
            celery_compat=True,
        )

        @app.task()
        async def task_with_metadata(arg: str) -> str:
            """Test task."""
            return arg.upper()

        # Build message
        delay_ctx = task_with_metadata.delay("hello")
        message = delay_ctx.build_delay_message()

        # Decode and verify metadata
        decoded = json.loads(message.decode("utf-8"))

        # Verify Celery Protocol v2 structure
        assert "properties" in decoded
        assert "headers" in decoded
        assert "body" in decoded

        # Verify properties
        properties = decoded["properties"]
        assert properties["content_type"] == "application/json"
        assert properties["content_encoding"] == "utf-8"
        assert properties["delivery_mode"] == 2  # Persistent
        assert "correlation_id" in properties

        # Verify headers
        headers = decoded["headers"]
        assert headers["lang"] == "py"
        assert headers["task"] == "task_with_metadata"
        assert headers["retries"] == 0
        assert "id" in headers

        # Verify body
        body = decoded["body"]
        assert body["args"] == ["hello"]
        assert isinstance(body["kwargs"], dict)

    async def test_mixed_format_detection(self):
        """Test that worker can detect both AioTasks and Celery format messages."""
        # Celery-format message
        from aiotasks.celery_compat import encode_celery_task

        celery_msg = encode_celery_task(
            task_name="process",
            args=[42],
            serializer="json",
        )

        # AioTasks-format message
        aiotasks_msg = msgpack.packb(
            {
                "task_id": "test123",
                "function": "process",
                "args": [100],
                "kwargs": {},
            },
            use_bin_type=True,
        )

        # Verify format detection
        assert is_celery_message(celery_msg) is True
        assert is_celery_message(aiotasks_msg) is False

        # Verify both can be decoded by their respective decoders
        celery_decoded = decode_celery_task(celery_msg, serializer="json")
        assert celery_decoded["task_name"] == "process"
        assert celery_decoded["args"] == [42]

        aiotasks_decoded = msgpack.unpackb(aiotasks_msg, raw=False)
        assert aiotasks_decoded["function"] == "process"
        assert aiotasks_decoded["args"] == [100]


@pytest.mark.asyncio()
class TestCeleryCompatibilityFeatures:
    """Test specific Celery compatibility features."""

    async def test_task_id_format(self):
        """Test that task IDs are UUID4 format when celery_compat=True."""
        app = AioTasks(
            name="test_task_id",
            broker="memory://",
            celery_compat=True,
        )

        @app.task()
        async def test_task() -> None:
            """Test task."""

        delay_ctx = test_task.delay()
        message = delay_ctx.build_delay_message()

        decoded = decode_celery_task(message, serializer="json")
        task_id = decoded["task_id"]

        # Verify it's a valid UUID4
        assert len(task_id) == 36
        uuid_obj = uuid.UUID(task_id, version=4)
        assert str(uuid_obj) == task_id

    async def test_args_kwargs_serialization(self):
        """Test complex args/kwargs serialization in Celery format."""
        app = AioTasks(
            name="test_serialization",
            broker="memory://",
            celery_compat=True,
        )

        @app.task()
        async def complex_task(
            *args: int | str | float,
            **kwargs: int | str | bool | None,
        ) -> dict:
            """Task with complex arguments."""
            return {"args": args, "kwargs": kwargs}

        # Test with complex arguments
        delay_ctx = complex_task.delay(
            1,
            "string",
            3.14,
            flag=True,
            name="test",
            count=42,
            optional=None,
        )
        message = delay_ctx.build_delay_message()

        decoded = decode_celery_task(message, serializer="json")

        assert decoded["args"] == [1, "string", 3.14]
        assert decoded["kwargs"] == {
            "flag": True,
            "name": "test",
            "count": 42,
            "optional": None,
        }

    async def test_celery_compat_default_false(self):
        """Test that celery_compat defaults to False."""
        app = AioTasks(
            name="test_default",
            broker="memory://",
            # celery_compat not specified, should default to False
        )

        @app.task()
        async def default_task() -> None:
            """Test task."""

        delay_ctx = default_task.delay()
        message = delay_ctx.build_delay_message()

        # Should use AioTasks native format by default
        assert is_celery_message(message) is False

    async def test_celery_format_round_trip(self):
        """Test that Celery messages can be encoded and decoded correctly."""
        from aiotasks.celery_compat import encode_celery_task

        # Original data
        task_name = "tasks.calculate"
        args = [10, 20]
        kwargs = {"operation": "add", "debug": True}
        task_id = str(uuid.uuid4())

        # Encode
        encoded = encode_celery_task(
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            task_id=task_id,
            serializer="json",
        )

        # Verify it's Celery format
        assert is_celery_message(encoded) is True

        # Decode
        decoded = decode_celery_task(encoded, serializer="json")

        # Verify round-trip
        assert decoded["task_name"] == task_name
        assert decoded["args"] == args
        assert decoded["kwargs"] == kwargs
        assert decoded["task_id"] == task_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
