# AioTasks

<div align="center">

**🚀 Modern Async Task Queue for Python 3.12+**

*A Celery-like task manager that distributes asyncio coroutines*

[![PyPI version](https://badge.fury.io/py/aiotasks.svg)](https://pypi.org/project/aiotasks/)
[![Python versions](https://img.shields.io/pypi/pyversions/aiotasks.svg)](https://pypi.org/project/aiotasks/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](https://github.com/cr0hn/aiotasks/blob/main/LICENSE)
[![CI/CD](https://github.com/cr0hn/aiotasks/workflows/CI%2FCD/badge.svg)](https://github.com/cr0hn/aiotasks/actions)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://aiotasks.readthedocs.io)

[Features](#-features) •
[Installation](#-installation) •
[Quick Start](#-quick-start) •
[CLI Reference](#-cli-reference) •
[Migration Guide](#-migration-from-10x) •
[Documentation](https://aiotasks.readthedocs.io)

</div>

---

## 📋 Table of Contents

- [What is AioTasks?](#-what-is-aiotasks)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Examples](#-examples)
- [CLI Reference](#-cli-reference)
- [Backends](#-backends)
- [Migration from 1.0.x](#-migration-from-10x)
- [What's New in 2.0](#-whats-new-in-20)
- [Why AioTasks?](#-why-aiotasks)
- [License](#-license)

---

## 🎯 What is AioTasks?

AioTasks is a **modern, high-performance task queue** built on Python's asyncio. If you're familiar with Celery, you'll feel right at home - AioTasks provides a **nearly identical API** but is designed specifically for async/await workflows.

**Perfect for:**
- 🌐 Web applications (FastAPI, aiohttp, Django async)
- 📧 Background task processing (emails, notifications, reports)
- 🔄 Periodic tasks and scheduling
- 📊 Data pipelines and ETL jobs
- 🤖 Microservices communication

---

## ✨ Features

- **🎭 Celery-Compatible CLI** - Same syntax, just `aiotasks` instead of `celery`
- **⚡ Native AsyncIO** - Built from scratch for async/await
- **🔄 Multiple Backends** - Memory, Redis, RabbitMQ (AMQP), ZeroMQ
- **🏊 Pool Support** - async (coroutines), thread, or process pools (Celery-like `--pool`)
- **🔁 Smart Retry Logic** - Exponential backoff with tenacity
- **📊 Task Acknowledgment** - Reliable ACK/NACK support
- **⏱️ TTL Support** - Automatic task expiration
- **🎯 Type Safe** - Complete type hints with modern Python
- **🐍 Python 3.12+** - Pattern matching, StrEnum, PEP 604, type aliases
- **📝 Comprehensive Testing** - pytest suite with 40%+ coverage
- **🔄 CI/CD Ready** - GitHub Actions workflows included
- **📚 Multi-Language Docs** - English & Spanish

---

## 📦 Installation

**One command installs everything:**

```bash
pip install aiotasks
```

### 🎁 What's Included?

✅ **All Brokers**: Redis, RabbitMQ (AMQP), ZeroMQ, Memory
✅ **Performance**: uvloop, ujson
✅ **FastAPI**: Full integration included
✅ **CLI Tools**: Celery-compatible commands
✅ **Type Safety**: Complete type hints

**No optional dependencies needed** - everything is included by default!

---

## 🚀 Quick Start

### 1. Define Your App (Celery-Style)

```python
import asyncio
from aiotasks import AioTasks

# Create app (just like Celery!)
app = AioTasks("myapp", broker="redis://localhost:6379/0")

# Define tasks
@app.task()
async def send_email(to: str, subject: str, body: str):
    await asyncio.sleep(1)  # Simulate sending
    print(f"📧 Email sent to {to}")
    return {"status": "sent"}
```

### 2. Run the Worker

```bash
# Celery-compatible CLI - same syntax!
aiotasks -A myapp worker -l INFO -c 10
```

### 3. Queue Tasks

```python
async def main():
    app.run()
    await send_email.delay("user@example.com", "Hello", "World!")
    await app.wait(timeout=10, exit_on_finish=True)
    app.stop()

asyncio.run(main())
```

---

## 💡 Examples

### Modern Python Features

```python
from enum import StrEnum, auto

class Priority(StrEnum):
    URGENT = auto()
    HIGH = auto()
    NORMAL = auto()

@app.task()
async def send_notification(
    user_id: int,
    message: str,
    priority: Priority = Priority.NORMAL,
) -> dict[str, str | int]:
    # Python 3.10+ pattern matching
    match priority:
        case Priority.URGENT:
            delay = 0
        case Priority.HIGH:
            delay = 0.1
        case _:
            delay = 0.5

    await asyncio.sleep(delay)
    return {"user_id": user_id, "status": "sent"}
```

### Pool Support - Choose Your Execution Strategy

**New in v2.3**: AioTasks supports three execution pool types (like Celery's `--pool`):

```python
# Async pool (default) - for I/O-bound async tasks
app = AioTasks('myapp', broker='redis://localhost', pool='async')

@app.task()
async def fetch_data(url: str):
    await asyncio.sleep(1)  # Non-blocking I/O
    return data

# Thread pool - for blocking I/O and sync libraries
app = AioTasks('myapp', broker='redis://localhost', pool='thread', concurrency=20)

@app.task()
def blocking_io(file_path: str):
    import time
    time.sleep(1)  # Blocking call OK in thread pool
    return result

# Process pool - for CPU-intensive tasks
app = AioTasks('myapp', broker='redis://localhost', pool='process', concurrency=4)

@app.task()
def cpu_intensive(n: int):
    # True parallel execution (bypasses GIL)
    return sum(i*i for i in range(n))
```

**CLI:**
```bash
# Run worker with specific pool type
aiotasks -A app worker --pool=async -c 10    # Default (coroutines)
aiotasks -A app worker --pool=thread -c 20   # Thread pool
aiotasks -A app worker --pool=process -c 4   # Process pool
```

**When to use each:**
- **async**: I/O-bound async tasks (DB queries, API calls, file I/O)
- **thread**: Blocking I/O, legacy sync code, sync libraries
- **process**: CPU-intensive tasks, bypasses GIL for true parallelism

### Integration with FastAPI

**Recommended approach** - API sends tasks, workers run separately:

```python
from fastapi import FastAPI
from aiotasks import AioTasks

# Step 1: Create FastAPI app and AioTasks instance
api = FastAPI()
tasks = AioTasks("api_tasks", broker="redis://localhost:6379/0")

# Step 2: Define background tasks
@tasks.task()
async def send_welcome_email(email: str, name: str):
    """This will be executed by separate workers."""
    await asyncio.sleep(2)
    print(f"📧 Welcome email sent to {name} ({email})")
    return {"status": "sent", "email": email}

@tasks.task()
async def process_order(order_id: int, user_id: int):
    """Heavy processing executed by workers."""
    await asyncio.sleep(5)
    print(f"✅ Order {order_id} processed for user {user_id}")
    return {"order_id": order_id, "status": "completed"}

# Step 3: API endpoints - they just queue tasks!
@api.post("/register")
async def register_user(email: str, name: str):
    # Queue task - workers will process it
    await send_welcome_email.delay(email, name)
    return {"status": "registered", "message": "Email will be sent"}

@api.post("/orders")
async def create_order(order_id: int, user_id: int):
    # Queue task - workers will process it
    await process_order.delay(order_id, user_id)
    return {"order_id": order_id, "status": "processing"}
```

**Run it:**
```bash
# Terminal 1: Start Redis
docker run -d -p 6379:6379 redis:alpine

# Terminal 2: Run FastAPI (API only, no workers)
uvicorn app:api --reload

# Terminal 3: Run workers separately (recommended for production)
aiotasks -A app.tasks worker -l INFO -c 10
```

**Alternative: In-process worker (development only)**

If you need workers in the same process, run them in a separate thread:

```python
import threading
from fastapi import FastAPI
from aiotasks import AioTasks

api = FastAPI()
tasks = AioTasks("api_tasks", broker="redis://localhost")

@tasks.task()
async def background_task(data: str):
    # Process in background
    pass

@api.on_event("startup")
async def startup():
    # Run worker in a separate thread, NOT in the async context
    def run_worker():
        tasks.run()  # This blocks, so it must run in a thread

    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()

@api.post("/process")
async def process(data: str):
    await background_task.delay(data)
    return {"status": "queued"}
```

**Why separate workers?**
- ✅ **Scalable** - Run multiple workers: `aiotasks worker -c 20`
- ✅ **Reliable** - API and workers can restart independently
- ✅ **Production-ready** - Standard architecture for async task queues
- ✅ **Resource isolation** - Workers don't compete with API for resources

**Install with FastAPI support:**
```bash
pip install aiotasks[fastapi,redis]
```

---

## 🖥️ CLI Reference

**Celery-compatible CLI** - The syntax is nearly identical!

```bash
# Start worker
aiotasks -A myapp worker -l INFO -c 10

# With specific queues
aiotasks -A myapp worker -Q high,normal,low

# Inspect tasks
aiotasks inspect active
aiotasks inspect stats

# Control workers
aiotasks control shutdown

# Show status
aiotasks status
```

---

## 🔧 Backends

| Backend | Use Case | Persistence | Performance |
|---------|----------|-------------|-------------|
| Memory | Development | ❌ | ⚡⚡⚡ |
| Redis | Production | ✅ | ⚡⚡⚡ |
| RabbitMQ | Enterprise | ✅ | ⚡⚡ |
| ZeroMQ | High-perf | ❌ | ⚡⚡⚡ |

```python
# Memory (development)
app = AioTasks("dev", broker="memory://")

# Redis (production - recommended)
app = AioTasks("prod", broker="redis://localhost:6379/0")

# RabbitMQ (enterprise)
app = AioTasks("enterprise", broker="amqp://guest:guest@localhost/")

# ZeroMQ (high performance)
app = AioTasks("fast", broker="zmq://localhost:5555")
```

---

## 🔄 Migration from 1.0.x

### Before (v1.x)

```python
from aiotasks import build_manager

manager = build_manager("redis://localhost")

@manager.task()
async def my_task():
    pass
```

### After (v2.x - Recommended)

```python
from aiotasks import AioTasks

app = AioTasks("myapp", broker="redis://localhost")

@app.task()
async def my_task():
    pass
```

**Note:** Both APIs work! The classic API is still supported. ✅

---

## 🆕 What's New in 2.0

### Major Features
- ✅ **Celery-Compatible CLI** - Same commands, familiar syntax
- ✅ **Modern API** - `AioTasks` class mimics Celery
- ✅ **Python 3.12+ Support** - Pattern matching, StrEnum, type aliases, modern type hints
- ✅ **Retry Logic** - Automatic retries with exponential backoff
- ✅ **ACK/NACK** - Reliable task processing
- ✅ **TTL Support** - Task expiration
- ✅ **Pydantic v2** - Modern data validation

### Infrastructure
- ✅ **pytest Suite** - Modern testing (40%+ coverage)
- ✅ **GitHub Actions** - Complete CI/CD
- ✅ **MkDocs** - Beautiful documentation
- ✅ **Type Safety** - Full type hints

### Breaking Changes
- Requires Python >=3.12 (was >=3.7)
- Removed deprecated booby
- Updated msgpack compatibility

See [CHANGELOG.md](CHANGELOG.md) for details.

---

## 🤔 Why AioTasks?

### vs Celery

- ✅ **Native Async** - No worker processes needed
- ✅ **Modern Python** - Uses 3.12+ features
- ✅ **Type Safe** - Complete type hints
- ✅ **Simpler** - Memory backend for development
- ✅ **Compatible** - Easy migration

### vs TaskIQ / ARQ

- ✅ **Celery-Compatible** - Familiar API
- ✅ **More Backends** - 4+ supported
- ✅ **Built-in Retry** - Sophisticated logic
- ✅ **Full CLI** - Complete tooling
- ✅ **Easy Migration** - From Celery

---

## 📚 Documentation

- 📖 **Full Docs**: [aiotasks.readthedocs.io](https://aiotasks.readthedocs.io)
- 🚀 **Quick Start**: [Getting Started Guide](https://aiotasks.readthedocs.io/getting-started/quickstart/)
- 📘 **API Reference**: [API Docs](https://aiotasks.readthedocs.io/api/aiotasks/)
- 💡 **Examples**: [examples_new/](examples_new/)
- 🌍 **Languages**: English & Spanish

---

## 📄 License

**BSD-3-Clause License**

```
Copyright (c) 2024, Daniel Garcia (cr0hn)
All rights reserved.
```

See [LICENSE](LICENSE) for full text.

---

<div align="center">

**Made with ❤️ by [cr0hn](https://github.com/cr0hn)**

⭐ **Star us on GitHub** if you find AioTasks useful!

[GitHub](https://github.com/cr0hn/aiotasks) •
[PyPI](https://pypi.org/project/aiotasks/) •
[Documentation](https://aiotasks.readthedocs.io)

</div>
