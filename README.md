# AioTasks

<div align="center">

**🚀 Modern Async Task Queue for Python 3.12+**

*A Celery-like task manager that distributes asyncio coroutines*

[![PyPI version](https://badge.fury.io/py/aiotasks.svg)](https://pypi.org/project/aiotasks/)
[![Python versions](https://img.shields.io/pypi/pyversions/aiotasks.svg)](https://pypi.org/project/aiotasks/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](https://github.com/cr0hn/aiotasks/blob/main/LICENSE)
[![CI/CD](https://github.com/cr0hn/aiotasks/workflows/CI%2FCD/badge.svg)](https://github.com/cr0hn/aiotasks/actions)

</div>

---


## 📋 Table of Contents

- [What is AioTasks?](#-what-is-aiotasks)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Core Concepts](#-core-concepts)
- [Result Backend](#-result-backend)
- [Periodic Tasks](#-periodic-tasks)
- [Dead Letter Queue](#-dead-letter-queue)
- [Celery Interoperability](#-celery-interoperability)
- [Pool Support](#-pool-support)
- [Backends](#-backends)
- [CLI Reference](#-cli-reference)
- [Examples](#-examples)
- [Migration Guide](#-migration-guide)
- [FAQ](#-faq)
- [Contributing](#-contributing)
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
- 🔗 Celery integration and gradual migration

---


## ✨ Features

### Core Features

- **🎭 Celery-Compatible API** - Same syntax, just `aiotasks` instead of `celery`
- **⚡ Native AsyncIO** - Built from scratch for async/await
- **🔄 Multiple Backends** - Memory, Redis, RabbitMQ (AMQP), ZeroMQ
- **🏊 Pool Support** - async (coroutines), thread, or process pools (Celery-like `--pool`)
- **🔁 Smart Retry Logic** - Exponential backoff with tenacity
- **📊 Task Acknowledgment** - Reliable ACK/NACK support
- **⏱️ TTL Support** - Automatic task expiration
- **🎯 Type Safe** - Complete type hints with modern Python
- **🐍 Python 3.12+** - Pattern matching, StrEnum, PEP 604, type aliases

### 🔗 Celery Interoperability **NEW in v2.3**

**Full Celery Protocol v2 compatibility** enables seamless interoperability:

- Send tasks from AioTasks, process with Celery workers
- Send tasks from Celery, process with AioTasks workers
- Mixed worker pools (some Celery, some AioTasks)
- Gradual migration from Celery to AioTasks
- FastAPI + existing Celery infrastructure

```python
# Enable with one parameter
app = AioTasks(
    'myapp',
    broker='redis://localhost:6379/0',
    celery_compat=True,  # ✨ That's it!
)
```

### 📦 Result Backend **NEW in v2.3**

**Store and retrieve task results** with multiple backends:

- Get task results by ID
- Wait for task completion with timeout
- Memory and Redis backends
- Automatic result expiration (TTL)

```python
# Configure result backend
app = AioTasks(
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',  # Results stored here
)

# Get results
result = await app.wait_for_result(task_id, timeout=60)
print(result.result)  # Task return value
```

### ⏰ Periodic Tasks **NEW in v2.3**

**Celery Beat compatible scheduler** for periodic tasks:

- Interval schedules (every N seconds/minutes/hours)
- Cron-style schedules
- Start/stop scheduler independently
- Persistent schedule configuration

```python
from aiotasks import every, crontab

# Every hour
app.add_periodic_task(
    name="cleanup",
    schedule=every(hours=1),
    task="cleanup_old_data",
)

# Daily at 7:30 AM
app.add_periodic_task(
    name="daily_report",
    schedule=crontab(hour="7", minute="30"),
    task="generate_report",
)

await app.start_scheduler()
```

### 💀 Dead Letter Queue **NEW in v2.3**

**Handle failed tasks gracefully**:

- Automatic DLQ for tasks that exhaust retries
- Inspect failed tasks with full error details
- Retry failed tasks manually or in batch
- DLQ statistics and monitoring

```python
# List failed tasks
failed = await app.list_failed_tasks(limit=10)

# Retry specific failed task
await app.retry_failed_task(task_id)

# Retry all failed email tasks
count = await app.retry_failed_tasks(task_name="send_email")

# Get statistics
stats = app.get_dlq_stats()
print(f"Total failed: {stats['total_tasks']}")
```

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


## 📦 Result Backend

### Overview

The Result Backend allows you to store and retrieve task results. This is essential for APIs that need to wait for task completion or check task status.

### Configuration

```python
from aiotasks import AioTasks

# Memory backend (development)
app = AioTasks(
    broker='memory://',
    backend='memory://',  # Results in memory
)

# Redis backend (production)
app = AioTasks(
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',  # Results in Redis
    task_ttl=3600,  # Results expire after 1 hour
)
```

### Usage

```python
# Define task
@app.task()
async def calculate(x: int, y: int) -> int:
    await asyncio.sleep(2)
    return x + y

# Queue task and get task ID
task_ctx = calculate.delay(4, 5)
task_id = task_ctx.task_id

# Option 1: Poll for result
result = await app.get_result(task_id)
if result and result.status == "success":
    print(result.result)  # 9

# Option 2: Wait for result (with timeout)
try:
    result = await app.wait_for_result(task_id, timeout=30)
    print(result.result)  # 9
except TimeoutError:
    print("Task didn't complete in time")
except RuntimeError as e:
    print(f"Task failed: {e}")
```

### Result Object

```python
class TaskResult:
    task_id: str          # Task identifier
    status: str           # pending, started, success, failure
    result: Any           # Return value (if successful)
    error: str            # Error message (if failed)
    traceback: str        # Full traceback (if failed)
    started_at: datetime  # When task started
    completed_at: datetime  # When task completed
```

### FastAPI Integration

```python
from fastapi import FastAPI, BackgroundTasks
from aiotasks import AioTasks

app_api = FastAPI()
tasks = AioTasks(broker='redis://...', backend='redis://...')

@app_api.post("/process")
async def process_data(data: dict):
    # Queue task
    task_ctx = process_job.delay(data)

    return {"task_id": task_ctx.task_id, "status": "processing"}

@app_api.get("/status/{task_id}")
async def get_status(task_id: str):
    result = await tasks.get_result(task_id)

    if result is None:
        return {"status": "not_found"}

    return {
        "status": result.status,
        "result": result.result if result.status == "success" else None,
        "error": result.error if result.status == "failure" else None,
    }
```

---

## ⏰ Periodic Tasks

### Overview

Periodic tasks allow you to schedule tasks to run automatically at specific intervals or times, similar to Celery Beat.

### Creating Schedules

```python
from aiotasks import AioTasks, every, crontab

app = AioTasks(broker='redis://localhost:6379/0')

# Define your tasks
@app.task()
async def cleanup_old_data():
    # Cleanup logic
    pass

@app.task()
async def send_daily_report():
    # Report logic
    pass

@app.task()
async def health_check():
    # Health check logic
    pass
```

### Interval Schedules

Run tasks at fixed intervals:

```python
# Every 30 seconds
app.add_periodic_task(
    name="health_check",
    schedule=every(seconds=30),
    task="health_check",
)

# Every 5 minutes
app.add_periodic_task(
    name="quick_cleanup",
    schedule=every(minutes=5),
    task="cleanup_old_data",
)

# Every 2 hours
app.add_periodic_task(
    name="hourly_sync",
    schedule=every(hours=2),
    task="sync_data",
)

# Every day
app.add_periodic_task(
    name="daily_backup",
    schedule=every(days=1),
    task="backup_database",
)
```

### Cron Schedules

Use cron-style expressions for more complex schedules:

```python
# Every 15 minutes
app.add_periodic_task(
    name="frequent_check",
    schedule=crontab(minute="*/15"),
    task="check_status",
)

# Daily at 7:30 AM
app.add_periodic_task(
    name="morning_report",
    schedule=crontab(hour="7", minute="30"),
    task="send_daily_report",
)

# Every Monday at 9 AM
app.add_periodic_task(
    name="weekly_cleanup",
    schedule=crontab(hour="9", minute="0", day_of_week="1"),
    task="weekly_maintenance",
)

# First day of month at midnight
app.add_periodic_task(
    name="monthly_billing",
    schedule=crontab(hour="0", minute="0", day_of_month="1"),
    task="process_billing",
)

# Every 2 hours at :30 (2:30, 4:30, 6:30, etc.)
app.add_periodic_task(
    name="bi_hourly",
    schedule=crontab(hour="*/2", minute="30"),
    task="sync_external_data",
)
```

### Starting the Scheduler

```python
# Start worker and scheduler together
async def main():
    # Start task worker
    app.run()

    # Start periodic scheduler
    await app.start_scheduler()

    # Wait for tasks
    await app.wait()

# Or start scheduler separately
await app.start_scheduler()

# Stop scheduler
await app.stop_scheduler()
```

### Managing Periodic Tasks

```python
# List all periodic tasks
tasks = app.list_periodic_tasks()
for task in tasks:
    print(f"{task.name}: {task.total_runs} runs")

# Get specific task
task = app.get_periodic_task("daily_report")
print(f"Last run: {task.last_run}")

# Remove periodic task
app.remove_periodic_task("old_task")

# Disable temporarily
task = app.get_periodic_task("cleanup")
task.enabled = False
```

### Dynamic Schedules

```python
# Add task with parameters
app.add_periodic_task(
    name="parameterized_task",
    schedule=every(hours=1),
    task="process_category",
    kwargs={"category": "emails", "limit": 100},
)

# Add task programmatically
def setup_monitoring(app, services):
    for service in services:
        app.add_periodic_task(
            name=f"monitor_{service}",
            schedule=every(minutes=5),
            task="monitor_service",
            kwargs={"service": service},
        )
```

---

## 💀 Dead Letter Queue (DLQ)

### Overview

The Dead Letter Queue automatically captures tasks that fail after exhausting all retry attempts, allowing you to:

- Inspect failed tasks with full error details
- Retry failed tasks manually or in batch
- Debug production issues
- Monitor failure patterns

### How It Works

When a task fails all retry attempts (default 3), it's automatically moved to the DLQ:

```python
from aiotasks import AioTasks

app = AioTasks(
    broker='redis://localhost:6379/0',
    max_retries=3,  # After 3 retries, task goes to DLQ
)

@app.task()
async def risky_operation(data: dict):
    # This might fail
    result = await external_api.call(data)
    return result
```

### Inspecting Failed Tasks

```python
# List all failed tasks
failed_tasks = await app.list_failed_tasks(limit=10)

for task in failed_tasks:
    print(f"Task: {task.task_name}")
    print(f"Error: {task.error}")
    print(f"Retries: {task.retry_count}")
    print(f"Failed at: {task.failed_at}")
    print(f"Traceback: {task.traceback}")

# Get specific failed task
failed = await app.get_failed_task(task_id)
if failed:
    print(f"Args: {failed.args}")
    print(f"Kwargs: {failed.kwargs}")

# Filter by task name
failed_emails = await app.list_failed_tasks(
    task_name="send_email",
    limit=20,
)
```

### Retrying Failed Tasks

```python
# Retry single task
success = await app.retry_failed_task(task_id)
if success:
    print("Task queued for retry")

# Retry all failed tasks of specific type
count = await app.retry_failed_tasks(task_name="send_email")
print(f"Retried {count} email tasks")

# Retry all failed tasks (up to limit)
count = await app.retry_failed_tasks(limit=50)
print(f"Retried {count} tasks")
```

### Clearing the DLQ

```python
# Clear all failed tasks
count = await app.clear_failed_tasks()
print(f"Cleared {count} failed tasks")

# Clear only specific task type
count = await app.clear_failed_tasks(task_name="send_email")
print(f"Cleared {count} failed email tasks")
```

### DLQ Statistics

```python
stats = app.get_dlq_stats()

print(f"Total failed tasks: {stats['total_tasks']}")
print(f"Max DLQ size: {stats['max_size']}")
print(f"Oldest failure: {stats['oldest_failure']}")
print(f"Newest failure: {stats['newest_failure']}")

# Failures by task type
for task_name, count in stats['by_task_name'].items():
    print(f"{task_name}: {count} failures")
```

### Monitoring Failed Tasks

```python
# Periodic check for failed tasks
@app.task()
async def monitor_dlq():
    stats = app.get_dlq_stats()

    if stats['total_tasks'] > 100:
        # Send alert
        await send_alert(f"DLQ has {stats['total_tasks']} failed tasks!")

    # Log failure patterns
    for task_name, count in stats['by_task_name'].items():
        if count > 10:
            logging.warning(f"Task {task_name} has {count} failures")

# Schedule monitoring
app.add_periodic_task(
    name="dlq_monitor",
    schedule=every(minutes=5),
    task="monitor_dlq",
)
```

### Production Best Practices

```python
# 1. Set appropriate retry limits
app = AioTasks(
    broker='redis://...',
    max_retries=5,  # More retries before DLQ
)

# 2. Monitor DLQ size
async def check_dlq_health():
    stats = app.get_dlq_stats()
    if stats['total_tasks'] > 1000:
        # DLQ getting full - investigate
        await alert_ops_team(stats)

# 3. Automatic retry of transient failures
async def auto_retry_transient():
    # Retry tasks that might have failed due to temporary issues
    failed = await app.list_failed_tasks(task_name="api_call")

    for task in failed:
        if "connection" in task.error.lower():
            # Likely transient - retry
            await app.retry_failed_task(task.task_id)

# 4. Archive old failures
async def archive_old_failures():
    failed = await app.list_failed_tasks()

    for task in failed:
        age = (datetime.utcnow() - task.failed_at).days
        if age > 30:
            # Archive to database
            await db.archive_failed_task(task)
            # Remove from DLQ
            await app.dlq.remove_task(task.task_id)
```

---


## 🔗 Celery Interoperability
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

