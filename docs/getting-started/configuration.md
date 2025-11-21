# Configuration

Learn how to configure AioTasks for different use cases.

## Basic Configuration

```python
from aiotasks import AioTasks

app = AioTasks(
    name="myapp",              # Application name
    broker="memory://",        # Broker DSN
    concurrency=5,             # Max concurrent tasks
    max_retries=3,             # Max retry attempts
    task_ttl=3600,            # Task time-to-live (seconds)
)
```

## Broker Configuration

### Memory Backend (Development)

Perfect for development and testing:

```python
app = AioTasks("myapp", broker="memory://")
```

- No external dependencies
- Tasks stored in memory
- Lost on restart

### Redis Backend (Production)

Recommended for production:

```python
app = AioTasks(
    "myapp",
    broker="redis://localhost:6379/0",
    concurrency=10,
)
```

With authentication:

```python
broker = "redis://:password@localhost:6379/0"
app = AioTasks("myapp", broker=broker)
```

### RabbitMQ/AMQP Backend

For enterprise deployments:

```python
broker = "amqp://guest:guest@localhost:5672/"
app = AioTasks("myapp", broker=broker)
```

### ZeroMQ Backend

For high-performance messaging:

```python
broker = "zmq://localhost:5555"
app = AioTasks("myapp", broker=broker)
```

## Task Configuration

### Concurrency

Control how many tasks run simultaneously:

```python
# Low concurrency (I/O bound tasks)
app = AioTasks("myapp", broker="redis://localhost", concurrency=5)

# High concurrency (many small tasks)
app = AioTasks("myapp", broker="redis://localhost", concurrency=50)
```

### Retry Configuration

Configure retry behavior:

```python
app = AioTasks(
    "myapp",
    broker="redis://localhost",
    max_retries=5,        # Retry up to 5 times
)
```

Retry uses exponential backoff:
- 1st retry: ~4 seconds
- 2nd retry: ~8 seconds
- 3rd retry: ~16 seconds
- 4th retry: ~32 seconds
- 5th retry: ~60 seconds (capped)

### Task TTL (Time-To-Live)

Prevent old tasks from accumulating:

```python
app = AioTasks(
    "myapp",
    broker="redis://localhost",
    task_ttl=3600,  # Tasks expire after 1 hour
)
```

## Environment Variables

Configure via environment variables:

```python
import os
from aiotasks import AioTasks

broker = os.getenv("AIOTASKS_BROKER", "memory://")
concurrency = int(os.getenv("AIOTASKS_CONCURRENCY", "5"))

app = AioTasks("myapp", broker=broker, concurrency=concurrency)
```

Example `.env` file:

```bash
AIOTASKS_BROKER=redis://localhost:6379/0
AIOTASKS_CONCURRENCY=10
AIOTASKS_MAX_RETRIES=3
AIOTASKS_TASK_TTL=7200
```

## Production Recommendations

### Redis Configuration

```python
from aiotasks import AioTasks

app = AioTasks(
    name="production_app",
    broker="redis://redis.prod:6379/0",
    concurrency=20,           # Adjust based on your workload
    max_retries=3,            # Reasonable default
    task_ttl=86400,          # 24 hours
)
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  worker:
    build: .
    depends_on:
      - redis
    environment:
      - AIOTASKS_BROKER=redis://redis:6379/0
      - AIOTASKS_CONCURRENCY=10
    command: python worker.py

volumes:
  redis_data:
```

## Next Steps

- [Quick Start](quickstart.md)
- [Celery-Style API](../guide/celery-style.md)
- [Retry & Error Handling](../guide/retry.md)
