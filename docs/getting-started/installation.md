# Installation

## Requirements

- Python 3.11 or higher
- pip

## Basic Installation

Install AioTasks from PyPI:

```bash
pip install aiotasks
```

This installs the core package with the memory backend only.

## Installation with Backends

### Redis Backend

```bash
pip install aiotasks[redis]
```

Includes Redis support with hiredis for better performance.

### RabbitMQ/AMQP Backend

```bash
pip install aiotasks[amqp]
```

Includes support for RabbitMQ and other AMQP brokers via aio-pika.

### ZeroMQ Backend

```bash
pip install aiotasks[zeromq]
```

Includes support for ZeroMQ messaging.

### Performance Optimizations

```bash
pip install aiotasks[performance]
```

Includes:
- uvloop for faster event loop
- ujson for faster JSON serialization

### FastAPI Integration

```bash
pip install aiotasks[fastapi]
```

Includes FastAPI and Uvicorn for building web APIs with AioTasks.

### All Features

```bash
pip install aiotasks[all]
```

Installs everything including all backends and optimizations.

## Development Installation

For contributors and developers:

```bash
# Clone the repository
git clone https://github.com/cr0hn/aiotasks.git
cd aiotasks

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

The dev installation includes:
- pytest for testing
- ruff for linting
- mypy for type checking
- pre-commit for git hooks

## Verification

Verify your installation:

```python
>>> import aiotasks
>>> aiotasks.__version__
'2.0.0'
>>> from aiotasks import AioTasks
>>> app = AioTasks("test", broker="memory://")
>>> print(app)
<AioTasks app='test' broker='memory://'>
```

## Docker Installation

You can also run AioTasks in Docker:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install AioTasks with Redis backend
RUN pip install aiotasks[redis]

COPY . /app

CMD ["python", "worker.py"]
```

## Next Steps

- [Quick Start Tutorial](quickstart.md)
- [Configuration Guide](configuration.md)
