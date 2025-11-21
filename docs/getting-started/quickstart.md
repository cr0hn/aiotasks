# Quick Start

This guide will help you get up and running with AioTasks in minutes.

## Installation

First, install AioTasks:

```bash
pip install aiotasks
```

## Your First Task

Create a file `my_tasks.py`:

```python
import asyncio
from aiotasks import AioTasks

# Create the app
app = AioTasks("myapp", broker="memory://")

# Define a task
@app.task()
async def hello(name: str) -> str:
    """Say hello to someone."""
    await asyncio.sleep(1)  # Simulate work
    return f"Hello, {name}!"

# Run the application
async def main():
    # Start the worker
    app.run()

    # Queue some tasks
    await hello.delay("Alice")
    await hello.delay("Bob")
    await hello.delay("Charlie")

    # Wait for tasks to complete
    await app.wait(timeout=10, exit_on_finish=True)

    # Stop the worker
    app.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python my_tasks.py
```

## Using Redis Backend

For production, use Redis:

```python
import asyncio
from aiotasks import AioTasks

# Use Redis backend
app = AioTasks(
    "myapp",
    broker="redis://localhost:6379/0",
    concurrency=10,
    max_retries=3,
)

@app.task()
async def process_data(data: dict) -> dict:
    """Process some data."""
    # Your processing logic here
    return {"status": "processed", "data": data}

async def main():
    app.run()

    # Queue many tasks
    for i in range(100):
        await process_data.delay({"id": i, "value": i * 2})

    await app.wait(timeout=60, exit_on_finish=True)
    app.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Task with Error Handling

```python
@app.task()
async def risky_operation(value: int) -> int:
    """An operation that might fail."""
    if value % 3 == 0:
        raise ValueError("Value is divisible by 3!")
    return value * 2

# AioTasks will automatically retry failed tasks up to max_retries times
```

## Modern Python Features

AioTasks supports modern Python 3.11+ features:

```python
from enum import StrEnum, auto

class Priority(StrEnum):
    """Task priority levels."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    URGENT = auto()

@app.task()
async def send_notification(
    user_id: int,
    message: str,
    priority: Priority = Priority.NORMAL,
) -> dict[str, str | int]:
    """Send a notification with priority."""

    # Use pattern matching (Python 3.10+)
    match priority:
        case Priority.URGENT:
            delay = 0
        case Priority.HIGH:
            delay = 0.1
        case Priority.NORMAL:
            delay = 0.5
        case Priority.LOW:
            delay = 1.0

    await asyncio.sleep(delay)

    return {
        "user_id": user_id,
        "status": "sent",
        "message": message,
    }
```

## Next Steps

- Learn about [Configuration](configuration.md)
- Explore the [Celery-Style API](../guide/celery-style.md)
- Check out [Advanced Examples](../examples/advanced.md)
- Read about [Retry & Error Handling](../guide/retry.md)
