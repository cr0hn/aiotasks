# 🚀 aiotasks

**A modern, Celery-like task queue for Python 3.12+ using asyncio**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: BSD-3](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

---

## 🌟 What's New in v2.0

**aiotasks** has been completely modernized for Python 3.12+:

- ✨ **Modern Python 3.12+** - Full type hints with PEP 604 syntax
- 🔄 **New Backends** - Redis, RabbitMQ (AMQP), ZeroMQ support
- ⚡ **Performance** - Built on `redis.asyncio` and `uvloop`
- 🎯 **FastAPI Integration** - Seamless FastAPI integration module
- 📦 **UV Package Manager** - Modern dependency management
- 🔍 **Quality Tools** - Ruff, mypy, pylint, pre-commit hooks
- 📚 **Comprehensive Docs** - Full type hints and examples

---

## 📋 Features

- **Async-First**: Built from the ground up with `asyncio`
- **Multiple Backends**: Memory, Redis, RabbitMQ, ZeroMQ
- **Celery-like API**: Familiar `@task` decorator and `.delay()` pattern
- **Pub/Sub Support**: Topic-based message subscriptions
- **Type Safe**: Complete type hints for excellent IDE support
- **Production Ready**: Battle-tested patterns and error handling
- **Fast**: Non-blocking, event-driven architecture
- **Easy Integration**: Works seamlessly with FastAPI, aiohttp, and more

---

## 🚀 Quick Start

### Installation

```bash
# Basic installation (Memory + Redis)
pip install aiotasks

# With all backends
pip install aiotasks[all]

# Individual backends
pip install aiotasks[redis]      # Redis support
pip install aiotasks[amqp]       # RabbitMQ support
pip install aiotasks[zeromq]     # ZeroMQ support
pip install aiotasks[fastapi]    # FastAPI integration
```

### Basic Usage (Celery-style API - Recommended)

```python
import asyncio
from aiotasks import AioTasks

# Create app (just like Celery!)
app = AioTasks("myapp", broker="redis://localhost:6379/0")

# Define tasks
@app.task
async def send_email(to: str, subject: str, body: str):
    await asyncio.sleep(1)  # Simulate email sending
    print(f"Email sent to {to}")

# Use tasks
async def main():
    app.run()  # Start worker

    # Queue tasks for async execution
    await send_email.delay("user@example.com", "Hello", "World")

    # Wait for completion
    await app.wait(timeout=10, exit_on_finish=True)
    app.stop()

asyncio.run(main())
```

<details>
<summary>Alternative: Classic API (still supported)</summary>

```python
import asyncio
from aiotasks import build_manager

# Create a task manager
manager = build_manager("redis://localhost:6379/0")

# Define a task
@manager.task()
async def send_email(to: str, subject: str, body: str):
    await asyncio.sleep(1)
    print(f"Email sent to {to}")

# Use the task
async def main():
    manager.run()
    await send_email.delay("user@example.com", "Hello", "World")
    await manager.wait(timeout=10, exit_on_finish=True)
    manager.stop()

asyncio.run(main())
```
</details>

---

## 🔌 Backend Support

### Redis (Production)

```python
from aiotasks import build_manager

manager = build_manager("redis://localhost:6379/0")
```

Perfect for production deployments with persistent task queues.

### RabbitMQ / AMQP (Enterprise)

```python
manager = build_manager("amqp://guest:guest@localhost:5672/")
```

Ideal for enterprise environments requiring reliable message delivery.

### ZeroMQ (High Performance)

```python
manager = build_manager("zmq://localhost:5555")
```

Best for ultra-low latency and high-throughput scenarios.

### Memory (Development)

```python
manager = build_manager("memory://")
```

Perfect for development and testing.

---

## 🌐 FastAPI Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiotasks.integrations.fastapi import aiotasks_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with aiotasks_lifespan(
        app,
        dsn="redis://localhost:6379/0"
    ) as state:
        yield state

app = FastAPI(lifespan=lifespan)

@app.state.aiotasks.task()
async def process_upload(file_id: int):
    # Process file asynchronously
    pass

@app.post("/upload")
async def upload_file(file_id: int):
    await process_upload.delay(file_id)
    return {"status": "processing"}
```

See `examples_new/fastapi/` for complete examples.

---

## 📖 Documentation

- **[Quick Start Guide](docs/quickstart.md)** - Get started in 5 minutes
- **[API Reference](docs/api.md)** - Complete API documentation
- **[Examples](examples_new/)** - Real-world usage examples
- **[Backends](docs/backends.md)** - Backend configuration guide
- **[FastAPI Integration](docs/fastapi.md)** - FastAPI integration guide

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  Your Application                │
│  (FastAPI, aiohttp, Django Ninja, etc.)          │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│              aiotasks Manager                    │
│  • Task Registration                             │
│  • Task Routing                                  │
│  • Concurrency Control                           │
└──────────────────┬──────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
 ┌────────┐  ┌────────┐  ┌────────┐
 │ Redis  │  │ RabbitMQ│ │ ZeroMQ │
 │Backend │  │ Backend │ │Backend │
 └────────┘  └────────┘  └────────┘
```

---

## 🔬 Development

### Setup

```bash
# Clone the repository
git clone https://github.com/cr0hn/aiotasks.git
cd aiotasks

# Create virtual environment with uv
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
uv pip install -e ".[dev,all]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=aiotasks --cov-report=html

# Run specific tests
pytest tests/test_redis.py
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy aiotasks

# Run all checks
pre-commit run --all-files
```

---

## 📊 Comparison with Celery

| Feature | aiotasks | Celery |
|---------|----------|--------|
| Async/Await | ✅ Native | ⚠️ Limited |
| Python Version | 3.12+ | 3.8+ |
| Type Hints | ✅ Complete | ⚠️ Partial |
| Redis Support | ✅ Native async | ✅ Sync |
| RabbitMQ Support | ✅ Native async | ✅ Sync |
| ZeroMQ Support | ✅ Native async | ❌ No |
| FastAPI Integration | ✅ Built-in | ⚠️ Manual |
| Learning Curve | 🟢 Low | 🟡 Medium |
| Performance | 🚀 Very Fast | ⚡ Fast |

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📜 License

This project is licensed under the BSD-3-Clause License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Credits

**Author**: Daniel Garcia (cr0hn) - [@ggdaniel](https://twitter.com/ggdaniel)

**Contributors**: See [CONTRIBUTORS.md](CONTRIBUTORS.md)

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

## 📬 Support

- **Issues**: [GitHub Issues](https://github.com/cr0hn/aiotasks/issues)
- **Discussions**: [GitHub Discussions](https://github.com/cr0hn/aiotasks/discussions)
- **Twitter**: [@ggdaniel](https://twitter.com/ggdaniel)

---

Made with ❤️ by the aiotasks community
