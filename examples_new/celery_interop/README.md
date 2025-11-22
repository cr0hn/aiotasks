# AioTasks + Celery Interoperability Example

This example demonstrates **full interoperability** between AioTasks and Celery, enabling you to:

- 🚀 Use **FastAPI with AioTasks** to send tasks
- ⚡ Process tasks with **Celery workers** (existing infrastructure)
- 🔄 **Gradual migration** from Celery to AioTasks
- 🏗️ **Mixed deployments** (some workers use Celery, some use AioTasks)
- 🎯 Choose the **best worker** for each task type

## Architecture

```
┌─────────────┐
│   FastAPI   │  Sends tasks using AioTasks API
│  + AioTasks │  (celery_compat=True)
└──────┬──────┘
       │ Celery Protocol v2 messages
       ▼
┌─────────────┐
│    Redis    │  Shared message broker
└──────┬──────┘
       │
       ├──────► Celery Worker (legacy, CPU-intensive)
       │
       └──────► AioTasks Worker (async I/O, modern)
```

## Key Feature: `celery_compat=True`

The magic happens with one parameter:

```python
tasks = AioTasks(
    name="myapp",
    broker="redis://localhost:6379/0",
    celery_compat=True,  # ✨ Enable Celery Protocol v2 format
)
```

This ensures:
- ✅ Tasks are sent in **Celery Protocol v2** format
- ✅ **Celery workers** can process them
- ✅ **AioTasks workers** can also process them
- ✅ **No code changes** needed in existing Celery workers!

## Files in This Example

- `fastapi_producer.py` - FastAPI app sending tasks via AioTasks
- `celery_worker.py` - Traditional Celery worker processing tasks
- `aiotasks_worker.py` - Modern AioTasks worker (async/await)
- `docker-compose.yml` - Complete stack with Redis
- `Dockerfile` - Container image for all services

## Quick Start with Docker Compose

### 1. Start Everything

```bash
docker-compose up
```

This starts:
- **Redis** (port 6379) - Message broker
- **FastAPI** (port 8000) - API sending tasks
- **Celery Worker** - Processing tasks
- **Flower** (port 5555) - Celery monitoring UI

### 2. Send Tasks via API

```bash
# Send email task
curl -X POST http://localhost:8000/send-email/user@example.com

# Process data task
curl -X POST http://localhost:8000/process-data \
  -H "Content-Type: application/json" \
  -d '{"key": "value", "count": 42}'

# Generate report task
curl -X POST http://localhost:8000/generate-report/123
```

### 3. Watch the Logs

```bash
# Watch Celery worker process the tasks
docker-compose logs -f celery-worker

# Watch FastAPI logs
docker-compose logs -f fastapi
```

### 4. Monitor with Flower

Open http://localhost:5555 in your browser to see:
- Active tasks
- Worker status
- Task history
- Performance metrics

## Manual Setup (Without Docker)

### 1. Install Dependencies

```bash
# For the FastAPI producer
pip install fastapi uvicorn aiotasks[redis]

# For the Celery worker
pip install celery redis flower
```

### 2. Start Redis

```bash
docker run -d -p 6379:6379 redis:alpine
```

### 3. Start Celery Worker

```bash
celery -A celery_worker worker --loglevel=info
```

### 4. Start FastAPI Application

```bash
python fastapi_producer.py
```

### 5. Send Tasks

```bash
curl -X POST http://localhost:8000/send-email/test@example.com
```

## Using AioTasks Worker Instead

To use AioTasks workers instead of (or alongside) Celery workers:

### 1. Uncomment in docker-compose.yml

```yaml
aiotasks-worker:
  build: .
  command: python aiotasks_worker.py
  # ... rest of config
```

### 2. Or run manually:

```bash
python aiotasks_worker.py
```

### 3. Both workers can run simultaneously!

Tasks will be distributed round-robin between Celery and AioTasks workers. You can:
- Run **both** for high availability
- Choose **Celery** for CPU-intensive tasks
- Choose **AioTasks** for async I/O tasks

## Use Cases

### 1. Gradual Migration from Celery

**Week 1:** Keep existing Celery workers, add FastAPI with AioTasks
```python
# New FastAPI code uses AioTasks
tasks = AioTasks(broker="redis://...", celery_compat=True)

# Existing Celery workers process tasks - no changes needed!
```

**Week 2-N:** Gradually replace Celery workers with AioTasks workers
```bash
# Decommission old Celery workers one by one
# Start new AioTasks workers to replace them
```

**Final state:** Pure AioTasks, full async/await benefits

### 2. Mixed Deployment by Task Type

```python
# Use Celery workers for CPU-intensive tasks
@celery_app.task
def process_image(image_data):
    return expensive_cpu_operation(image_data)

# Use AioTasks workers for I/O-bound tasks
@aiotasks_app.task
async def send_webhook(url, data):
    async with httpx.AsyncClient() as client:
        await client.post(url, json=data)
```

### 3. FastAPI with Existing Celery Infrastructure

```python
# Your new FastAPI app
tasks = AioTasks("myapp", broker="redis://...", celery_compat=True)

# Works with your existing Celery workers!
# No need to rewrite or redeploy worker code
```

## Message Format Comparison

### AioTasks sends this (with celery_compat=True):

```json
{
  "properties": {
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "content_type": "application/json",
    "delivery_mode": 2
  },
  "headers": {
    "task": "send_email",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "lang": "py",
    "retries": 0
  },
  "body": {
    "args": ["user@example.com"],
    "kwargs": {"subject": "Hello"}
  }
}
```

### Celery worker sees this - and processes it normally! ✅

## API Documentation

Once FastAPI is running, visit:
- **Interactive docs:** http://localhost:8000/docs
- **Alternative docs:** http://localhost:8000/redoc

## Monitoring

### Flower (Celery)
- URL: http://localhost:5555
- Shows: Active tasks, workers, history

### FastAPI Logs
```bash
docker-compose logs -f fastapi
```

### Worker Logs
```bash
# Celery worker
docker-compose logs -f celery-worker

# AioTasks worker (if enabled)
docker-compose logs -f aiotasks-worker
```

## Testing

### 1. Verify Celery Compatibility

```python
from aiotasks.celery_compat import is_celery_message, encode_celery_task

# Create a task message
msg = encode_celery_task(
    task_name="test_task",
    args=[1, 2],
    kwargs={"flag": True}
)

# Verify it's in Celery format
assert is_celery_message(msg) is True
```

### 2. Integration Test

```bash
# Run the integration tests
pytest tests/integration/test_celery_interop.py -v
```

## Performance Considerations

### AioTasks Workers (Async)
- **Best for:** I/O-bound tasks (HTTP, database, file I/O)
- **Concurrency:** High (100+ tasks with minimal overhead)
- **Blocking code:** Use `pool='thread'` parameter

### Celery Workers (Sync)
- **Best for:** CPU-intensive tasks, legacy code
- **Concurrency:** Limited by number of processes
- **Stability:** Battle-tested, mature ecosystem

### Mixed Strategy (Recommended)
- **Celery:** CPU-intensive tasks, legacy code
- **AioTasks:** New async tasks, high I/O concurrency
- **Both:** Share the same Redis broker, work together seamlessly

## Troubleshooting

### Tasks not being processed

**Check Redis connection:**
```bash
docker exec -it $(docker ps -qf "name=redis") redis-cli PING
# Should return: PONG
```

**Check task queue:**
```bash
docker exec -it $(docker ps -qf "name=redis") redis-cli LLEN myapp:tasks
# Shows number of pending tasks
```

### Worker not starting

**Check logs:**
```bash
docker-compose logs celery-worker
docker-compose logs aiotasks-worker
```

**Verify Redis connectivity:**
```bash
docker-compose exec celery-worker ping redis -c 1
```

### Tasks stuck in queue

**Check worker concurrency:**
```yaml
# In docker-compose.yml
celery-worker:
  command: celery -A celery_worker worker --loglevel=info --concurrency=8
  # Increase concurrency ^^^
```

## Learn More

- [AioTasks Documentation](https://github.com/cr0hn/aiotasks)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Celery Protocol v2 Specification](https://docs.celeryq.dev/en/stable/internals/protocol.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## License

This example is part of the AioTasks project.
