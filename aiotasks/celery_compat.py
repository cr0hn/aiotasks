"""Celery message protocol compatibility layer.

This module provides full compatibility with Celery v5+ message protocol,
enabling interoperability between AioTasks and Celery workers.

Protocol Details:
- Implements Celery Protocol Version 2
- Supports both JSON and msgpack serialization
- Compatible with Celery 5.0+

Use Cases:
1. Send tasks from AioTasks → Process with Celery workers
2. Send tasks from Celery → Process with AioTasks workers
3. Mix and match workers from both systems
4. Gradual migration from Celery to AioTasks

References:
- https://docs.celeryq.dev/en/stable/internals/protocol.html
"""

from __future__ import annotations

import socket
import uuid
from typing import Any

try:
    import ujson as json
except ImportError:
    import json

try:
    import umsgpack as msgpack
except ImportError:  # pragma: no cover
    import msgpack


def get_hostname() -> str:
    """Get current hostname for message origin."""
    return socket.gethostname()


def generate_task_id() -> str:
    """Generate Celery-compatible UUID task ID."""
    return str(uuid.uuid4())


def serialize_celery_message(
    task_name: str,
    args: tuple | list | None = None,
    kwargs: dict | None = None,
    task_id: str | None = None,
    retries: int = 0,
    eta: str | None = None,
    expires: str | None = None,
    timelimit: tuple[int | None, int | None] | None = None,
    serializer: str = "json",
    **extra: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Serialize task in Celery Protocol v2 format.

    Args:
        task_name: Name of the task to execute
        args: Positional arguments for the task
        kwargs: Keyword arguments for the task
        task_id: UUID for the task (auto-generated if None)
        retries: Number of retry attempts
        eta: ISO8601 timestamp for delayed execution
        expires: ISO8601 timestamp for task expiration
        timelimit: Tuple of (soft_limit, hard_limit) in seconds
        serializer: Serialization format ('json' or 'msgpack')
        **extra: Additional metadata to include in headers

    Returns:
        Tuple of (properties, headers, body) matching Celery v2 protocol

    Example:
        >>> props, headers, body = serialize_celery_message(
        ...     "tasks.add",
        ...     args=[4, 5],
        ...     kwargs={"debug": True}
        ... )
    """
    # Generate task ID if not provided
    if task_id is None:
        task_id = generate_task_id()

    # Normalize arguments
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    if timelimit is None:
        timelimit = (None, None)

    # Build properties (AMQP/broker-level metadata)
    properties = {
        "correlation_id": task_id,
        "content_type": "application/json" if serializer == "json" else "application/x-msgpack",
        "content_encoding": "utf-8",
        "reply_to": None,  # For result backend (not implemented yet)
        "delivery_mode": 2,  # Persistent
        "priority": 0,
    }

    # Build headers (task metadata)
    headers = {
        "lang": "py",
        "task": task_name,
        "id": task_id,
        "root_id": task_id,  # For task chains (simplified)
        "parent_id": None,
        "group": None,
        "meth": None,
        "shadow": None,
        "eta": eta,
        "expires": expires,
        "retries": retries,
        "timelimit": timelimit,
        "argsrepr": repr(args),
        "kwargsrepr": repr(kwargs),
        "origin": f"gen{uuid.uuid4().hex[:8]}@{get_hostname()}",
        "replaced_task_nesting": 0,
    }

    # Add any extra headers
    headers.update(extra)

    # Build body (task payload)
    body = {
        "args": list(args) if isinstance(args, tuple) else args,
        "kwargs": kwargs,
        "embed": {
            "callbacks": None,
            "errbacks": None,
            "chain": None,
            "chord": None,
        },
    }

    return properties, headers, body


def deserialize_celery_message(
    properties: dict[str, Any],
    headers: dict[str, Any],
    body: dict[str, Any],
) -> dict[str, Any]:
    """Deserialize Celery Protocol v2 message to AioTasks format.

    Args:
        properties: Message properties (correlation_id, content_type, etc.)
        headers: Task headers (lang, task, id, etc.)
        body: Task body (args, kwargs, embed)

    Returns:
        Dictionary with standardized task information

    Example:
        >>> task_info = deserialize_celery_message(props, headers, body)
        >>> print(task_info["task_id"], task_info["args"])
    """
    return {
        "task_id": headers.get("id") or properties.get("correlation_id"),
        "task_name": headers.get("task"),
        "args": body.get("args", []),
        "kwargs": body.get("kwargs", {}),
        "retries": headers.get("retries", 0),
        "eta": headers.get("eta"),
        "expires": headers.get("expires"),
        "timelimit": headers.get("timelimit"),
        "origin": headers.get("origin"),
        "root_id": headers.get("root_id"),
        "parent_id": headers.get("parent_id"),
        "group": headers.get("group"),
        "callbacks": body.get("embed", {}).get("callbacks"),
        "errbacks": body.get("embed", {}).get("errbacks"),
        "chain": body.get("embed", {}).get("chain"),
        "chord": body.get("embed", {}).get("chord"),
    }


def encode_celery_task(
    task_name: str,
    args: tuple | list | None = None,
    kwargs: dict | None = None,
    task_id: str | None = None,
    serializer: str = "json",
    **extra: Any,
) -> bytes:
    """Encode complete Celery task message for broker transmission.

    This combines properties, headers, and body into the final message format
    expected by Celery workers.

    Args:
        task_name: Name of the task to execute
        args: Positional arguments
        kwargs: Keyword arguments
        task_id: UUID for the task
        serializer: 'json' or 'msgpack'
        **extra: Additional headers

    Returns:
        Serialized message bytes ready for broker

    Example:
        >>> msg = encode_celery_task("tasks.add", args=[4, 5])
        >>> # Can be published directly to Redis/RabbitMQ
    """
    properties, headers, body = serialize_celery_message(
        task_name=task_name,
        args=args,
        kwargs=kwargs,
        task_id=task_id,
        serializer=serializer,
        **extra,
    )

    # Celery Protocol v2: headers separate from body
    message = {
        "properties": properties,
        "headers": headers,
        "body": body,
    }

    # Serialize based on content-type
    if serializer == "msgpack":
        return msgpack.packb(message, use_bin_type=True)
    return json.dumps(message).encode("utf-8")


def decode_celery_task(message: bytes, serializer: str = "json") -> dict[str, Any]:
    """Decode Celery task message from broker.

    Args:
        message: Raw message bytes from broker
        serializer: 'json' or 'msgpack'

    Returns:
        Parsed task information

    Example:
        >>> task_info = decode_celery_task(raw_message)
        >>> print(task_info["task_name"], task_info["args"])
    """
    # Deserialize message
    if serializer == "msgpack":
        data = msgpack.unpackb(message, raw=False)
    else:
        data = json.loads(message.decode("utf-8"))

    # Extract components
    properties = data.get("properties", {})
    headers = data.get("headers", {})
    body = data.get("body", {})

    # Convert to standardized format
    return deserialize_celery_message(properties, headers, body)


def is_celery_message(message: bytes | dict) -> bool:
    """Check if message follows Celery protocol format.

    Args:
        message: Raw message bytes or parsed dict

    Returns:
        True if message appears to be Celery format

    Example:
        >>> if is_celery_message(raw_msg):
        ...     task = decode_celery_task(raw_msg)
    """
    try:
        if isinstance(message, bytes):
            # Try JSON first
            try:
                data = json.loads(message.decode("utf-8"))
            except Exception:
                # Try msgpack
                data = msgpack.unpackb(message, raw=False)
        else:
            data = message

        # Check for Celery v2 protocol structure
        has_properties = "properties" in data
        has_headers = "headers" in data
        has_body = "body" in data
        has_task_header = "task" in data.get("headers", {})

        return has_properties and has_headers and has_body and has_task_header
    except Exception:
        return False


__all__ = (
    "decode_celery_task",
    "deserialize_celery_message",
    "encode_celery_task",
    "generate_task_id",
    "get_hostname",
    "is_celery_message",
    "serialize_celery_message",
)
