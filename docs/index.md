# AioTasks

**Modern async task queue for Python 3.12+** - A Celery-like task manager that distributes asyncio coroutines.

[![PyPI version](https://badge.fury.io/py/aiotasks.svg)](https://pypi.org/project/aiotasks/)
[![Python versions](https://img.shields.io/pypi/pyversions/aiotasks.svg)](https://pypi.org/project/aiotasks/)
[![License](https://img.shields.io/badge/license-BSD-blue.svg)](https://github.com/cr0hn/aiotasks/blob/main/LICENSE)
[![CI Status](https://github.com/cr0hn/aiotasks/workflows/CI%2FCD/badge.svg)](https://github.com/cr0hn/aiotasks/actions)

## What is AioTasks?

AioTasks is a modern, high-performance task queue built on Python's asyncio. If you're familiar with Celery, you'll feel right at home - AioTasks provides a similar API but designed specifically for async/await workflows.

## Key Features

- ✨ **Celery-like API**: Familiar interface for Python developers
- 🚀 **Native AsyncIO**: Built from the ground up for async/await
- 🔄 **Multiple Backends**: Memory, Redis, RabbitMQ (AMQP), ZeroMQ
- 🔁 **Smart Retry Logic**: Exponential backoff with tenacity
- 📊 **Task Acknowledgment**: ACK/NACK support for reliable processing
- ⏱️ **TTL Support**: Automatic task expiration
- 🎯 **Type Safe**: Complete type hints with modern Python syntax
- 🐍 **Python 3.12+**: Uses latest Python features (match/case, StrEnum, PEP 604)

## Quick Example

```python
import asyncio
from aiotasks import AioTasks

# Create app (just like Celery!)
app = AioTasks("myapp", broker="redis://localhost:6379/0")

# Define tasks
@app.task()
async def send_email(to: str, subject: str, body: str):
    await asyncio.sleep(1)  # Simulate sending email
    print(f"Email sent to {to}")

# Use tasks
async def main():
    app.run()
    await send_email.delay("user@example.com", "Hello", "World")
    await app.wait(timeout=10, exit_on_finish=True)
    app.stop()

asyncio.run(main())
```

## Why AioTasks?

### vs Celery

- **Native Async**: No need for worker processes, everything is coroutines
- **Modern Python**: Uses Python 3.12+ features like pattern matching
- **Simpler**: No need for separate broker processes in development (memory backend)
- **Type Safe**: Full type hints throughout

### vs TaskIQ/ARQ

- **Celery-compatible API**: Easier migration for existing projects
- **More Backends**: Support for Memory, Redis, AMQP, ZMQ
- **Built-in Retry**: Sophisticated retry logic with exponential backoff

## Installation

```bash
# Basic installation
pip install aiotasks

# With Redis support
pip install aiotasks

# With RabbitMQ support
pip install aiotasks

# With all features
pip install aiotasks
```

## Next Steps

- [Installation Guide](getting-started/installation.md)
- [Quick Start Tutorial](getting-started/quickstart.md)
- [User Guide](guide/celery-style.md)
- [Examples](examples/basic.md)
- [API Reference](api/aiotasks.md)

## License

AioTasks is distributed under the BSD-3-Clause license. See [LICENSE](https://github.com/cr0hn/aiotasks/blob/main/LICENSE) for more information.
