# Celery Interoperability

AioTasks provides **full interoperability** with Celery through Celery Protocol v2 support. This enables seamless integration between AioTasks and Celery workers, allowing for gradual migration, mixed deployments, and leveraging existing Celery infrastructure with modern async/await code.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Use Cases](#use-cases)
- [Configuration](#configuration)
- [Message Format](#message-format)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

## Overview

### What is Celery Compatibility?

When you enable `celery_compat=True`, AioTasks sends and receives task messages in **Celery Protocol v2** format instead of its native msgpack format. This means:

✅ **Celery workers can process tasks sent by AioTasks**
✅ **AioTasks workers can process tasks sent by Celery**
✅ **Both can share the same message broker (Redis, RabbitMQ, etc.)**
✅ **No code changes needed in existing Celery workers**
✅ **Gradual migration from Celery to AioTasks**

### Why Use This?

1. **Gradual Migration:** Migrate from Celery to AioTasks incrementally without downtime
2. **Mixed Deployments:** Run both Celery and AioTasks workers simultaneously
3. **Leverage Existing Infrastructure:** Use AioTasks with existing Celery setups
4. **Best of Both Worlds:** Use Celery for CPU tasks, AioTasks for async I/O tasks
5. **FastAPI Integration:** Modern async web frameworks with Celery worker pools

## Quick Start

### Enable Celery Compatibility

```python
from aiotasks import AioTasks

# Create AioTasks app with Celery compatibility
app = AioTasks(
    name="myapp",
    broker="redis://localhost:6379/0",
    celery_compat=True,  # ✨ Enable Celery interoperability
)

# Define tasks normally
@app.task()
async def send_email(to: str, subject: str) -> dict:
    # Your async code here
    return {"status": "sent", "to": to}

# Queue tasks normally
await send_email.delay("user@example.com", "Hello")
```

### Process with Celery Worker

```python
# celery_worker.py
from celery import Celery

app = Celery("myapp", broker="redis://localhost:6379/0")

@app.task(name="send_email")
def send_email(to: str, subject: str) -> dict:
    # Celery worker processes the task!
    return {"status": "sent", "to": to}
```

```bash
# Start the Celery worker
celery -A celery_worker worker --loglevel=info
```

**That's it!** AioTasks sends tasks in Celery format, and Celery workers process them.

## How It Works

### Message Format Conversion

When `celery_compat=True` is enabled:

#### Sending Tasks (Producer)

```python
# AioTasks with celery_compat=True
await send_email.delay("user@example.com", "Hello")
```

Produces this message (Celery Protocol v2):

```json
{
  "properties": {
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "content_type": "application/json",
    "content_encoding": "utf-8",
    "delivery_mode": 2
  },
  "headers": {
    "task": "send_email",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "lang": "py",
    "root_id": "550e8400-e29b-41d4-a716-446655440000",
    "retries": 0
  },
  "body": {
    "args": ["user@example.com", "Hello"],
    "kwargs": {},
    "embed": {
      "callbacks": null,
      "errbacks": null,
      "chain": null,
      "chord": null
    }
  }
}
```

#### Receiving Tasks (Consumer)

AioTasks workers with `celery_compat=True` can **auto-detect** both formats:

- **Celery Protocol v2** (JSON) → Processes normally
- **AioTasks native** (msgpack) → Also processes normally

This means workers can handle tasks from both AioTasks and Celery producers!

### Task ID Format

With `celery_compat=True`, task IDs are **UUID4** format (Celery standard):

```python
# Example task ID
"550e8400-e29b-41d4-a716-446655440000"
```

Without it, task IDs are hex strings:

```python
# Example task ID
"a1b2c3d4e5f6"
```

## Use Cases

### 1. Gradual Migration from Celery to AioTasks

**Scenario:** You have a large Celery codebase and want to migrate to AioTasks.

**Solution:** Migrate incrementally with zero downtime.

```python
# Week 1: New API code uses AioTasks
from aiotasks import AioTasks

tasks = AioTasks("myapp", broker="redis://...", celery_compat=True)

@tasks.task()
async def new_feature(data: dict):
    # New async code
    pass

# Existing Celery workers still process all tasks!
```

```python
# Weeks 2-N: Gradually replace Celery workers
# 1. Start AioTasks workers
# 2. Monitor both worker types
# 3. Decommission Celery workers when ready
```

**Benefits:**
- ✅ No big-bang migration
- ✅ Rollback-friendly
- ✅ Test in production incrementally
- ✅ Maintain existing Celery workers during transition

### 2. FastAPI + Celery Workers

**Scenario:** You're building a new FastAPI application but want to use existing Celery worker infrastructure.

**Solution:** Use AioTasks in FastAPI, keep Celery workers.

```python
# fastapi_app.py
from fastapi import FastAPI
from aiotasks import AioTasks

app = FastAPI()
tasks = AioTasks("api", broker="redis://...", celery_compat=True)

@tasks.task()
async def process_upload(file_id: int):
    return {"status": "processing", "file_id": file_id}

@app.post("/upload")
async def upload_file(file_id: int):
    await process_upload.delay(file_id)
    return {"message": "Processing started"}
```

```python
# celery_worker.py (existing)
from celery import Celery

app = Celery("api", broker="redis://...")

@app.task(name="process_upload")
def process_upload(file_id: int):
    # Existing Celery worker code - no changes!
    return {"status": "processing", "file_id": file_id}
```

**Benefits:**
- ✅ Modern async FastAPI code
- ✅ Leverage existing worker pools
- ✅ No infrastructure changes
- ✅ Full async/await in API layer

### 3. Mixed Worker Pools by Task Type

**Scenario:** Different tasks have different requirements.

**Solution:** Use the best worker for each task type.

```python
# For CPU-intensive tasks: Use Celery workers
@celery_app.task
def process_image(image_data: bytes):
    # CPU-intensive image processing
    return expensive_operation(image_data)

# For I/O-bound tasks: Use AioTasks workers
@aiotasks_app.task
async def send_webhooks(urls: list[str], data: dict):
    # Concurrent I/O with async/await
    async with httpx.AsyncClient() as client:
        tasks = [client.post(url, json=data) for url in urls]
        await asyncio.gather(*tasks)
```

**Worker Deployment:**
```bash
# CPU-intensive tasks → Celery workers (4 processes)
celery -A celery_tasks worker --concurrency=4 --loglevel=info

# I/O-bound tasks → AioTasks workers (100+ concurrent)
python aiotasks_worker.py  # High async concurrency
```

**Benefits:**
- ✅ Optimal resource utilization
- ✅ Choose the right tool for each job
- ✅ Both workers share same broker
- ✅ Unified monitoring and deployment

### 4. Multi-Language Workers

**Scenario:** Some tasks need to be processed by workers in other languages.

**Solution:** Use Celery Protocol v2 as the common interchange format.

```python
# Python: AioTasks sends tasks
tasks = AioTasks("polyglot", broker="redis://...", celery_compat=True)

await process_data.delay({"data": "value"})
```

```javascript
// Node.js: Celery worker in JavaScript
const celery = require('celery-node');
const client = celery.createClient({
  broker: 'redis://localhost:6379/0'
});

client.createWorker('process_data', async (data) => {
  // JavaScript worker processes the task!
  return { status: 'processed', data };
});
```

## Configuration

### AioTasks Configuration

```python
from aiotasks import AioTasks

app = AioTasks(
    name="myapp",              # Application name (Celery-compatible)
    broker="redis://...",      # Message broker DSN
    celery_compat=True,        # Enable Celery interoperability
    pool="async",              # Execution pool type
    concurrency=10,            # Max concurrent tasks
    max_retries=3,             # Max retry attempts
    task_ttl=3600,             # Task time-to-live (seconds)
)
```

### Celery Configuration

```python
from celery import Celery

app = Celery(
    "myapp",                   # Must match AioTasks name
    broker="redis://...",      # Must match AioTasks broker
    backend="redis://...",     # Optional result backend
)

app.conf.update(
    task_serializer="json",    # Match AioTasks celery_compat mode
    accept_content=["json"],   # Accept JSON messages
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

### Backend Support

All AioTasks backends support Celery compatibility:

| Backend | Celery Compat | Notes |
|---------|---------------|-------|
| Memory | ✅ | Development/testing only |
| Redis | ✅ | Recommended for production |
| RabbitMQ (AMQP) | ✅ | Enterprise deployments |
| ZeroMQ | ✅ | High-performance scenarios |

## Message Format

### Celery Protocol v2 Structure

Messages sent with `celery_compat=True` follow this structure:

```python
{
    "properties": {
        "correlation_id": str,      # Task ID (UUID4)
        "content_type": str,        # "application/json"
        "content_encoding": str,    # "utf-8"
        "delivery_mode": int,       # 2 (persistent)
    },
    "headers": {
        "task": str,                # Task name
        "id": str,                  # Task ID (same as correlation_id)
        "lang": str,                # "py"
        "root_id": str,             # Root task ID (for chains)
        "parent_id": str,           # Parent task ID (for chains)
        "group": str,               # Group ID (for groups)
        "retries": int,             # Retry count
        "eta": str,                 # ETA timestamp (optional)
        "expires": str,             # Expiration timestamp (optional)
        "argsrepr": str,            # String repr of args
        "kwargsrepr": str,          # String repr of kwargs
    },
    "body": {
        "args": list,               # Positional arguments
        "kwargs": dict,             # Keyword arguments
        "embed": {
            "callbacks": list,      # Success callbacks
            "errbacks": list,       # Error callbacks
            "chain": list,          # Chained tasks
            "chord": object,        # Chord configuration
        }
    }
}
```

### AioTasks Native Format (for comparison)

Without `celery_compat`, AioTasks uses a simpler msgpack format:

```python
{
    "task_id": str,           # Hex task ID
    "function": str,          # Function name
    "args": list,             # Positional arguments
    "kwargs": dict,           # Keyword arguments
}
```

## Migration Guide

### From Pure Celery to AioTasks

Follow this step-by-step migration path:

#### Phase 1: Preparation (Week 1)

1. **Audit your Celery codebase:**
   ```bash
   # Find all Celery tasks
   grep -r "@app.task" .
   grep -r "@celery.task" .
   ```

2. **Identify task dependencies:**
   - Which tasks call other tasks?
   - Which tasks use Celery-specific features (groups, chains, chords)?
   - Which tasks could benefit from async/await?

3. **Set up parallel test environment:**
   ```python
   # test_aiotasks_compat.py
   from aiotasks import AioTasks

   # Test AioTasks with Celery workers
   tasks = AioTasks("myapp", broker="redis://test:6379/0", celery_compat=True)
   ```

#### Phase 2: New Code with AioTasks (Weeks 2-4)

1. **New features use AioTasks:**
   ```python
   # new_features.py
   from aiotasks import AioTasks

   tasks = AioTasks("myapp", broker="redis://...", celery_compat=True)

   @tasks.task()
   async def new_async_feature(data: dict):
       # New async code
       async with httpx.AsyncClient() as client:
           response = await client.post("https://api.example.com", json=data)
           return response.json()
   ```

2. **Keep existing Celery workers running:**
   ```bash
   # No changes to existing workers
   celery -A myapp worker --loglevel=info
   ```

3. **Monitor both in production:**
   - Watch task success rates
   - Check for serialization issues
   - Verify task routing works correctly

#### Phase 3: Migrate Existing Tasks (Weeks 5-12)

1. **Convert tasks one module at a time:**
   ```python
   # Before (Celery)
   @app.task
   def send_email(to: str, subject: str):
       send_smtp_email(to, subject)
       return {"status": "sent"}

   # After (AioTasks - can be gradual!)
   @tasks.task()
   async def send_email(to: str, subject: str):
       await send_smtp_email_async(to, subject)
       return {"status": "sent"}
   ```

2. **Test converted tasks:**
   ```python
   # Test with both Celery and AioTasks workers
   pytest tests/tasks/test_email.py --workers=both
   ```

3. **Deploy incrementally:**
   ```bash
   # Week 5: 10% of tasks using AioTasks
   # Week 6: 25% of tasks using AioTasks
   # Week 7: 50% of tasks using AioTasks
   # ...
   ```

#### Phase 4: Worker Migration (Weeks 13-16)

1. **Start AioTasks workers:**
   ```bash
   # New AioTasks worker deployment
   python aiotasks_worker.py
   ```

2. **Run both worker types in parallel:**
   ```bash
   # Terminal 1: Celery workers (legacy)
   celery -A myapp worker --concurrency=4

   # Terminal 2: AioTasks workers (new)
   python aiotasks_worker.py  # Can handle both formats!
   ```

3. **Gradually reduce Celery workers:**
   - Monitor task distribution
   - Check error rates
   - Verify performance metrics
   - Scale down Celery, scale up AioTasks

#### Phase 5: Cleanup (Week 17+)

1. **Remove Celery dependency:**
   ```bash
   # Remove from requirements.txt
   # celery==5.3.0  # REMOVE

   pip uninstall celery
   ```

2. **Disable celery_compat (optional):**
   ```python
   # Once all Celery workers are gone
   tasks = AioTasks("myapp", broker="redis://...", celery_compat=False)
   # Slightly more efficient with native msgpack format
   ```

3. **Update documentation:**
   - Remove Celery references
   - Update deployment guides
   - Document the new async architecture

### From AioTasks to Add Celery Support

If you're already using AioTasks and want to add Celery workers:

```python
# Change one parameter
tasks = AioTasks(
    name="myapp",
    broker="redis://...",
    celery_compat=True,  # ← Just add this
)

# All existing code works unchanged!
```

Then start Celery workers that match your task names:

```python
# celery_worker.py
from celery import Celery

app = Celery("myapp", broker="redis://...")

# Define tasks matching AioTasks task names
@app.task(name="my_task_name")
def my_task_name(arg1, arg2):
    return process(arg1, arg2)
```

## Best Practices

### 1. Task Naming

Use consistent, descriptive names that work in both systems:

```python
# Good: Clear, matches across systems
@tasks.task()
async def send_email_notification(user_id: int, template: str):
    pass

@celery_app.task(name="send_email_notification")
def send_email_notification(user_id: int, template: str):
    pass
```

```python
# Bad: Generic names, easy to conflict
@tasks.task()
async def task1(data):
    pass
```

### 2. Serialization

Stick to JSON-serializable types for cross-system compatibility:

```python
# Good: JSON-serializable
await my_task.delay(
    user_id=123,
    data={"key": "value"},
    items=[1, 2, 3],
    flag=True,
)

# Bad: Not JSON-serializable
await my_task.delay(
    timestamp=datetime.now(),  # ❌ Can't serialize
    data=MyCustomObject(),     # ❌ Can't serialize
)

# Fix: Serialize manually
await my_task.delay(
    timestamp=datetime.now().isoformat(),  # ✅ String
    data=dataclasses.asdict(MyCustomObject()),  # ✅ Dict
)
```

### 3. Monitoring

Monitor both worker types during migration:

```python
# Track task metrics
import structlog

logger = structlog.get_logger()

@tasks.task()
async def monitored_task(data: dict):
    logger.info("task_started", task="monitored_task", worker="aiotasks")
    try:
        result = await process(data)
        logger.info("task_completed", task="monitored_task", worker="aiotasks")
        return result
    except Exception as e:
        logger.error("task_failed", task="monitored_task", error=str(e))
        raise
```

### 4. Error Handling

Handle errors consistently across both systems:

```python
# Define custom exceptions
class TaskError(Exception):
    pass

# Use in both AioTasks and Celery
@tasks.task()
async def safe_task(data: dict):
    try:
        return await process(data)
    except ValueError as e:
        raise TaskError(f"Invalid data: {e}") from e
    except Exception as e:
        raise TaskError(f"Processing failed: {e}") from e
```

### 5. Testing

Test with both worker types:

```python
# conftest.py
import pytest
from aiotasks import AioTasks

@pytest.fixture
def aiotasks_app():
    app = AioTasks("test", broker="memory://", celery_compat=True)
    yield app
    app.stop()

# test_tasks.py
@pytest.mark.asyncio
async def test_task_with_celery_format(aiotasks_app):
    @aiotasks_app.task()
    async def test_task(x: int) -> int:
        return x * 2

    # Build message
    ctx = test_task.delay(5)
    message = ctx.build_delay_message()

    # Verify Celery format
    from aiotasks.celery_compat import is_celery_message
    assert is_celery_message(message) is True
```

## Troubleshooting

### Tasks Not Being Processed

**Symptom:** Tasks queue up but workers don't process them.

**Diagnosis:**

```bash
# Check Redis queue length
redis-cli LLEN myapp:tasks

# Check if workers are connected
celery -A myapp inspect active
```

**Solutions:**

1. **Verify broker URL matches:**
   ```python
   # AioTasks
   tasks = AioTasks(broker="redis://localhost:6379/0", ...)

   # Celery
   app = Celery(broker="redis://localhost:6379/0")
   #                    ^^^^^^^^^^^^^^^^^^^^^^
   #                    Must match exactly!
   ```

2. **Check worker logs:**
   ```bash
   celery -A myapp worker --loglevel=debug
   ```

3. **Verify task names match:**
   ```python
   # AioTasks task name
   @tasks.task()  # → Uses function name: "my_task"
   async def my_task():
       pass

   # Celery must match
   @celery_app.task(name="my_task")  # ← Must be exact
   def my_task():
       pass
   ```

### Serialization Errors

**Symptom:** `TypeError: Object of type X is not JSON serializable`

**Solution:** Convert to JSON-serializable types:

```python
# Before
from datetime import datetime

@tasks.task()
async def task_with_date(timestamp: datetime):  # ❌ Not serializable
    pass

await task_with_date.delay(datetime.now())  # ❌ Error!

# After
@tasks.task()
async def task_with_date(timestamp: str):  # ✅ String
    actual_time = datetime.fromisoformat(timestamp)
    pass

await task_with_date.delay(datetime.now().isoformat())  # ✅ Works!
```

### Task Name Conflicts

**Symptom:** Wrong task executes, or `NotRegistered` error.

**Solution:** Use explicit task names:

```python
# Explicit naming (recommended)
@tasks.task(name="emails.send")
async def send_email():
    pass

@celery_app.task(name="emails.send")
def send_email():
    pass
```

### Performance Issues

**Symptom:** Tasks process slowly, workers seem idle.

**Solutions:**

1. **Increase concurrency:**
   ```bash
   # Celery
   celery -A myapp worker --concurrency=16

   # AioTasks
   tasks = AioTasks(concurrency=100, ...)  # Much higher for async!
   ```

2. **Use appropriate worker type:**
   ```python
   # CPU-bound → Celery or AioTasks with pool='process'
   tasks = AioTasks(pool="process", concurrency=4, ...)

   # I/O-bound → AioTasks with pool='async'
   tasks = AioTasks(pool="async", concurrency=100, ...)
   ```

3. **Monitor task duration:**
   ```python
   import time

   @tasks.task()
   async def monitored_task(data):
       start = time.time()
       result = await process(data)
       duration = time.time() - start
       print(f"Task took {duration:.2f}s")
       return result
   ```

## Examples

See the [examples_new/celery_interop/](../examples_new/celery_interop/) directory for complete working examples:

- `fastapi_producer.py` - FastAPI app using AioTasks
- `celery_worker.py` - Celery worker processing tasks
- `aiotasks_worker.py` - AioTasks worker (async)
- `docker-compose.yml` - Complete stack with Redis
- `README.md` - Detailed example documentation

## Further Reading

- [Celery Protocol v2 Specification](https://docs.celeryq.dev/en/stable/internals/protocol.html)
- [AioTasks Core Concepts](./core_concepts.md)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Migration Guide Example](../examples_new/celery_interop/README.md)

## Summary

Celery compatibility in AioTasks enables:

✅ **Seamless interoperability** with Celery workers
✅ **Gradual migration** from Celery to AioTasks
✅ **Mixed deployments** for optimal resource usage
✅ **Modern async/await** code with existing infrastructure
✅ **Zero-downtime** transitions

Just set `celery_compat=True` and you're ready to go!
