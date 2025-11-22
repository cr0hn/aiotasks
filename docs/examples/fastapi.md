# FastAPI Integration Guide

!!! success "Ultra-Simple Integration"
    Integrating AioTasks with FastAPI requires just **3 steps** and works seamlessly with FastAPI's async nature.

## Quick Start

### Step 1: Install Dependencies

```bash
# Install with FastAPI and Redis support
pip install aiotasks[fastapi,redis]
```

### Step 2: Create Your Application

Create a file `app.py`:

```python
from fastapi import FastAPI
from aiotasks import AioTasks
import asyncio

# Create FastAPI app and AioTasks instance
api = FastAPI()
tasks = AioTasks("api_tasks", broker="redis://localhost:6379/0")

# Define background tasks
@tasks.task()
async def send_welcome_email(email: str, name: str):
    """Send welcome email in the background."""
    await asyncio.sleep(2)  # Simulate email sending
    print(f"📧 Welcome email sent to {name} ({email})")
    return {"status": "sent", "email": email}

@tasks.task()
async def process_payment(payment_id: int, amount: float):
    """Process payment asynchronously."""
    await asyncio.sleep(3)  # Simulate payment processing
    print(f"💳 Payment {payment_id} processed: ${amount}")
    return {"payment_id": payment_id, "status": "completed"}

# Lifecycle management
@api.on_event("startup")
async def startup():
    """Start task worker on app startup."""
    tasks.run()

@api.on_event("shutdown")
async def shutdown():
    """Gracefully stop task worker on shutdown."""
    tasks.stop()

# API endpoints
@api.post("/register")
async def register_user(email: str, name: str):
    """Register user and send welcome email in background."""
    # Queue task - returns immediately
    await send_welcome_email.delay(email, name)
    return {"status": "registered", "message": "Welcome email will be sent"}

@api.post("/payments")
async def create_payment(payment_id: int, amount: float):
    """Create payment and process in background."""
    # Heavy processing happens asynchronously
    await process_payment.delay(payment_id, amount)
    return {"payment_id": payment_id, "status": "processing"}

@api.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "tasks": "running"}
```

### Step 3: Run Your Application

```bash
# Start Redis (required for this example)
docker run -d -p 6379:6379 redis:alpine

# Run the FastAPI app
uvicorn app:api --reload

# In another terminal, optionally run dedicated workers
aiotasks -A app.tasks worker -l INFO -c 10
```

## Testing the Integration

```bash
# Register a user
curl -X POST "http://localhost:8000/register?email=user@example.com&name=John"

# Create a payment
curl -X POST "http://localhost:8000/payments?payment_id=123&amount=99.99"

# Check health
curl http://localhost:8000/health
```

## Architecture Patterns

### Pattern 1: In-Process Worker (Development)

**Best for:** Development, testing, low-traffic apps

```python
from fastapi import FastAPI
from aiotasks import AioTasks

api = FastAPI()
tasks = AioTasks("myapp", broker="redis://localhost")

@tasks.task()
async def background_work():
    pass

@api.on_event("startup")
async def startup():
    tasks.run()  # Worker runs inside the FastAPI process
```

**Pros:**
- ✅ Simple setup
- ✅ Single process
- ✅ Easy debugging

**Cons:**
- ❌ Not scalable
- ❌ Tasks compete with API for resources

### Pattern 2: Separate Workers (Production)

**Best for:** Production, high-traffic, scalability

```python
# app.py - FastAPI application
from fastapi import FastAPI
from aiotasks import AioTasks

api = FastAPI()
tasks = AioTasks("myapp", broker="redis://production:6379/0")

@tasks.task()
async def heavy_processing(data: dict):
    """This will be processed by separate workers."""
    pass

@api.post("/process")
async def process_data(data: dict):
    # Queue task - separate workers will process it
    await heavy_processing.delay(data)
    return {"status": "queued"}

# NO @api.on_event("startup") - workers run separately!
```

```bash
# Terminal 1: Run FastAPI (API only, no workers)
uvicorn app:api --workers 4

# Terminal 2-N: Run dedicated workers
aiotasks -A app.tasks worker -c 20  # 20 concurrent tasks
aiotasks -A app.tasks worker -c 20  # Another worker
```

**Pros:**
- ✅ Highly scalable
- ✅ Independent scaling of API and workers
- ✅ Better resource utilization

**Cons:**
- ❌ More complex deployment
- ❌ Requires message broker (Redis/RabbitMQ)

### Pattern 3: Hybrid Approach

**Best for:** Mixed workloads (quick + heavy tasks)

```python
from fastapi import FastAPI
from aiotasks import AioTasks

api = FastAPI()

# Quick tasks - processed in-app
quick_tasks = AioTasks("quick", broker="redis://localhost", concurrency=5)

# Heavy tasks - processed by dedicated workers
heavy_tasks = AioTasks("heavy", broker="redis://localhost")

@quick_tasks.task()
async def send_notification(user_id: int):
    """Quick task - runs in-app."""
    await asyncio.sleep(0.5)

@heavy_tasks.task()
async def generate_report(report_id: int):
    """Heavy task - runs on separate workers."""
    await asyncio.sleep(60)

@api.on_event("startup")
async def startup():
    quick_tasks.run()  # Only quick tasks run in-app

@api.post("/notify/{user_id}")
async def notify(user_id: int):
    await send_notification.delay(user_id)
    return {"status": "notified"}

@api.post("/reports/{report_id}")
async def create_report(report_id: int):
    await generate_report.delay(report_id)
    return {"status": "generating"}
```

## Advanced Examples

### Task with Results

```python
from fastapi import FastAPI, BackgroundTasks
from aiotasks import AioTasks

api = FastAPI()
tasks = AioTasks("results", broker="redis://localhost")

# In-memory result storage (use Redis in production)
results = {}

@tasks.task()
async def analyze_data(analysis_id: str, data: list[int]):
    """Analyze data and store result."""
    await asyncio.sleep(2)
    result = {"mean": sum(data) / len(data), "count": len(data)}
    results[analysis_id] = result
    return result

@api.post("/analyze/{analysis_id}")
async def start_analysis(analysis_id: str, data: list[int]):
    await analyze_data.delay(analysis_id, data)
    return {"analysis_id": analysis_id, "status": "processing"}

@api.get("/analyze/{analysis_id}")
async def get_result(analysis_id: str):
    if analysis_id not in results:
        return {"status": "processing"}
    return {"status": "completed", "result": results[analysis_id]}
```

### Priority Queues

```python
from enum import StrEnum, auto
from aiotasks import AioTasks

class Priority(StrEnum):
    HIGH = auto()
    NORMAL = auto()
    LOW = auto()

tasks = AioTasks("priority", broker="redis://localhost")

@tasks.task()
async def process_task(task_id: int, priority: Priority):
    """Process with priority handling."""
    match priority:
        case Priority.HIGH:
            await asyncio.sleep(0.1)
        case Priority.NORMAL:
            await asyncio.sleep(0.5)
        case Priority.LOW:
            await asyncio.sleep(1.0)

    return {"task_id": task_id, "priority": priority}

@api.post("/tasks/urgent")
async def urgent_task(task_id: int):
    await process_task.delay(task_id, Priority.HIGH)
    return {"priority": "high"}
```

### Error Handling

```python
from fastapi import FastAPI, HTTPException
from aiotasks import AioTasks
import logging

logger = logging.getLogger(__name__)

tasks = AioTasks("errors", broker="redis://localhost", max_retries=3)

@tasks.task()
async def risky_operation(operation_id: int):
    """Operation that might fail."""
    try:
        # Simulate risky operation
        if operation_id % 3 == 0:
            raise ValueError("Operation failed")

        await asyncio.sleep(1)
        return {"operation_id": operation_id, "status": "success"}

    except Exception as e:
        logger.error(f"Operation {operation_id} failed: {e}")
        # Will retry automatically (max_retries=3)
        raise

@api.post("/operations/{operation_id}")
async def start_operation(operation_id: int):
    try:
        await risky_operation.delay(operation_id)
        return {"operation_id": operation_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Task Chaining

```python
@tasks.task()
async def step1_fetch_data(user_id: int) -> dict:
    """Step 1: Fetch user data."""
    await asyncio.sleep(1)
    return {"user_id": user_id, "data": "raw_data"}

@tasks.task()
async def step2_process_data(data: dict) -> dict:
    """Step 2: Process the data."""
    await asyncio.sleep(1)
    return {**data, "processed": True}

@tasks.task()
async def step3_save_result(result: dict) -> dict:
    """Step 3: Save the result."""
    await asyncio.sleep(1)
    return {**result, "saved": True}

@api.post("/pipeline/{user_id}")
async def run_pipeline(user_id: int):
    """Execute task pipeline."""
    # Note: Chain execution requires managing task results
    await step1_fetch_data.delay(user_id)
    return {"status": "pipeline started"}
```

## Configuration Best Practices

### Development Configuration

```python
from aiotasks import AioTasks

# Use memory backend for quick testing
tasks = AioTasks(
    "dev",
    broker="memory://",
    concurrency=2,
    max_retries=0,  # Fail fast in development
)
```

### Production Configuration

```python
from aiotasks import AioTasks
import os

tasks = AioTasks(
    "production",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    concurrency=20,  # Adjust based on workload
    max_retries=3,
    task_ttl=3600,  # Tasks expire after 1 hour
)
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  api:
    build: .
    command: uvicorn app:api --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

  worker:
    build: .
    command: aiotasks -A app.tasks worker -l INFO -c 20
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
    deploy:
      replicas: 3  # Run 3 workers
```

## Performance Tips

1. **Choose the Right Broker**
   - Development: `memory://` or `redis://localhost`
   - Production: Redis with connection pooling
   - Enterprise: RabbitMQ for reliability

2. **Tune Concurrency**
   - CPU-bound tasks: `concurrency = CPU cores`
   - I/O-bound tasks: `concurrency = 10-50` (experiment)
   - Mixed: Use separate workers

3. **Enable uvloop** (included by default)
   ```python
   # uvloop is automatically enabled with aiotasks
   # No manual configuration needed!
   ```

4. **Use Connection Pooling**
   ```python
   # Redis with connection pool
   tasks = AioTasks(
       "myapp",
       broker="redis://localhost?max_connections=50"
   )
   ```

## Monitoring and Health Checks

```python
from fastapi import FastAPI
from aiotasks import AioTasks

api = FastAPI()
tasks = AioTasks("myapp", broker="redis://localhost")

@api.get("/health/tasks")
async def task_health():
    """Monitor task system health."""
    return {
        "status": "healthy",
        "broker": tasks.broker_url,
        "concurrency": tasks._manager.concurrency,
        "tasks_registered": len(tasks._manager._tasks),
    }

@api.get("/metrics")
async def metrics():
    """Expose metrics for monitoring."""
    return {
        "tasks_total": len(tasks._manager._tasks),
        "workers_active": tasks._manager.concurrency,
        # Add more metrics as needed
    }
```

## Troubleshooting

### Issue: Tasks Not Processing

**Solution:** Check that workers are running and connected to the same broker.

```bash
# Verify Redis connection
redis-cli ping

# Check worker logs
aiotasks -A app.tasks worker -l DEBUG
```

### Issue: Slow Task Processing

**Solution:** Increase worker concurrency.

```bash
# Before
aiotasks -A app.tasks worker -c 5

# After
aiotasks -A app.tasks worker -c 20
```

### Issue: Memory Usage Growing

**Solution:** Set task TTL to expire old tasks.

```python
tasks = AioTasks("myapp", broker="redis://localhost", task_ttl=3600)
```

## Next Steps

- 📖 [Task Decorators](../guide/decorators.md)
- 📖 [Retry & Error Handling](../guide/retry.md)
- 📖 [Backends Configuration](../guide/backends.md)
- 💡 [Advanced Patterns](advanced.md)
