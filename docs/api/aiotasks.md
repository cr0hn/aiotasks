# AioTasks API Reference

::: aiotasks.app.AioTasks

## Overview

The `AioTasks` class is the main entry point for creating a Celery-like task queue application.

## Constructor

```python
AioTasks(
    name: str = "aiotasks",
    *,
    broker: str = "memory://",
    backend: str | None = None,
    concurrency: int = 5,
    max_retries: int = 3,
    task_ttl: int = 3600,
    **config: Any,
)
```

### Parameters

- **name** (`str`): Application name, used as prefix for task queues
- **broker** (`str`): Broker DSN (memory://, redis://, amqp://, zmq://)
- **backend** (`str | None`): Result backend DSN (future feature)
- **concurrency** (`int`): Maximum concurrent task executions
- **max_retries** (`int`): Maximum retry attempts for failed tasks
- **task_ttl** (`int`): Task time-to-live in seconds
- **config**: Additional configuration options

## Methods

### task()

Decorator to register async functions as tasks.

```python
@app.task(name: str | None = None, **options: Any)
async def my_task(...):
    ...
```

**Parameters:**
- `name`: Optional custom task name
- `options`: Additional task options (for future use)

**Returns:** Decorated function with `.delay()` method

**Example:**

```python
@app.task()
async def send_email(to: str, subject: str):
    await asyncio.sleep(1)
    print(f"Email sent to {to}")

# Queue the task
await send_email.delay("user@example.com", "Hello")
```

### run()

Start the task worker.

```python
app.run() -> None
```

Starts processing tasks from the queue. Call this before queuing any tasks.

### stop()

Stop the task worker.

```python
app.stop() -> None
```

Stops task processing and cleans up resources.

### wait()

Wait for tasks to complete.

```python
async def wait(
    *,
    timeout: float = 0,
    exit_on_finish: bool = False,
    wait_timeout: float = 1.0,
) -> None
```

**Parameters:**
- `timeout`: Maximum time to wait (0 = infinite)
- `exit_on_finish`: Exit when all tasks complete
- `wait_timeout`: Polling interval in seconds

**Example:**

```python
app.run()
await my_task.delay()
await app.wait(timeout=10, exit_on_finish=True)
app.stop()
```

## Complete Example

```python
import asyncio
from aiotasks import AioTasks

# Create application
app = AioTasks(
    "myapp",
    broker="redis://localhost:6379/0",
    concurrency=10,
    max_retries=3,
)

# Define task
@app.task()
async def process_item(item_id: int) -> dict:
    await asyncio.sleep(0.1)
    return {"id": item_id, "status": "processed"}

# Run worker
async def main():
    app.run()

    # Queue tasks
    for i in range(100):
        await process_item.delay(i)

    # Wait for completion
    await app.wait(timeout=60, exit_on_finish=True)

    app.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Type Hints

AioTasks is fully typed. Use modern Python type hints:

```python
@app.task()
async def typed_task(
    data: dict[str, int | float | str],
    options: dict[str, bool] | None = None,
) -> list[str]:
    results: list[str] = []
    for key, value in data.items():
        results.append(f"{key}: {value}")
    return results
```

## See Also

- [Backends Reference](backends.md)
- [Exceptions Reference](exceptions.md)
- [User Guide](../guide/celery-style.md)
