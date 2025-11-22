# AioTasks Examples

This directory contains comprehensive examples demonstrating how to use aiotasks with different backends and frameworks.

## Directory Structure

- `basic/` - Basic task usage examples
- `backends/` - Examples for each backend (Redis, AMQP, ZeroMQ)
- `fastapi/` - FastAPI integration examples
- `patterns/` - Common patterns and best practices

## Quick Start

### Basic Task Example

```python
import asyncio
from aiotasks import build_manager

# Create manager (memory backend for testing)
manager = build_manager("memory://")

# Define a task
@manager.task()
async def hello(name: str):
    await asyncio.sleep(1)
    print(f"Hello, {name}!")

# Queue the task
async def main():
    manager.run()
    await hello.delay("World")
    await manager.wait(timeout=5, exit_on_finish=True)
    manager.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Backend Examples

### Redis (Production)

```bash
# Start Redis
docker run -d -p 6379:6379 redis:latest

# Run example
python backends/redis_example.py
```

### RabbitMQ (AMQP)

```bash
# Start RabbitMQ
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:management

# Run example
python backends/amqp_example.py
```

### ZeroMQ (High Performance)

```bash
# No server needed - ZeroMQ is brokerless
python backends/zmq_example.py
```

## FastAPI Integration

See `fastapi/` directory for complete FastAPI applications with aiotasks.

```bash
# Run FastAPI example
cd fastapi
uvicorn app:app --reload
```

## Testing

All examples can be tested with:

```bash
pytest examples_new/
```
