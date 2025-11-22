# FastAPI + AioTasks Examples

This directory contains comprehensive examples of integrating AioTasks with FastAPI, from simple development setups to production-ready deployments.

!!! warning "Important"
    **Never** call `tasks.run()` directly in an async function! Use separate workers or threading (see examples below).

## 📋 Examples Overview

| Example | Workers | Complexity | Best For |
|---------|---------|------------|----------|
| `simple_integration.py` | **Separate** (recommended) | ⭐ Simple | Learning, production pattern |
| `simple_integration_threaded.py` | In-process (thread) | ⭐⭐ Medium | Development/testing only |
| `basic_app.py` | Lifespan integration | ⭐⭐ Medium | Advanced lifecycle management |
| `production_app.py` | **Separate** (production) | ⭐⭐⭐ Advanced | Production, scaling, priorities |
| `docker-compose.yml` | Docker deployment | ⭐⭐⭐ Advanced | Production containers |

## 🚀 Quick Start

### 1. Separate Workers (Recommended)

**File:** `simple_integration.py`

✅ **Best practice:** API queues tasks, workers process them in separate processes.

```bash
# Install dependencies
pip install aiotasks

# Terminal 1: Start Redis
docker run -d -p 6379:6379 redis:alpine

# Terminal 2: Run FastAPI (API only)
uvicorn simple_integration:api --reload

# Terminal 3: Run workers separately
aiotasks -A simple_integration.tasks worker -l INFO -c 10
```

**Test it:**
```bash
# Register a user (workers process it)
curl -X POST "http://localhost:8000/register?email=user@example.com&name=John"

# Create an order (workers process it)
curl -X POST "http://localhost:8000/orders?order_id=123&user_id=1"

# Check health
curl http://localhost:8000/health
```

**Architecture:**
```
┌──────────────┐               ┌──────────────┐
│ FastAPI API  │               │   Workers    │
│ (queues only)│               │ (process)    │
└──────┬───────┘               └──────┬───────┘
       │                              │
       └────────► Redis ◄─────────────┘
```

**Pros:**
- ✅ Production-ready pattern
- ✅ Scalable (add more workers)
- ✅ Resource isolation
- ✅ Independent restarts

**Cons:**
- ❌ Requires running workers separately

### 1b. In-Process Worker with Threading (Development Only)

**File:** `simple_integration_threaded.py`

⚠️ **Development only:** Workers run in same process via threading.

```bash
# Install dependencies
pip install aiotasks

# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Run the app (API + worker in same process)
python simple_integration_threaded.py
```

**Architecture:**
```
┌─────────────────────────────┐
│   FastAPI Process           │
│  ┌────────────────────────┐ │
│  │ API Endpoints          │ │
│  └────────────────────────┘ │
│  ┌────────────────────────┐ │
│  │ Worker Thread          │ │
│  └────────────────────────┘ │
└─────────────────────────────┘
         ↓ ↑
    ┌──────────┐
    │  Redis   │
    └──────────┘
```

**Pros:**
- ✅ Simple for quick testing
- ✅ Single process
- ✅ Easy debugging

**Cons:**
- ❌ Not scalable
- ❌ Not recommended for production
- ❌ Worker competes with API for resources

### 2. Production Deployment

**File:** `production_app.py`

Production-ready setup with separate API servers and task workers.

```bash
# Terminal 1: Run FastAPI (API only, no workers)
uvicorn production_app:api --workers 4 --host 0.0.0.0 --port 8000

# Terminal 2: Run high-priority workers
aiotasks -A production_app.tasks worker -l INFO -c 20 -Q high

# Terminal 3: Run normal-priority workers
aiotasks -A production_app.tasks worker -l INFO -c 10 -Q normal

# Terminal 4: Run low-priority workers
aiotasks -A production_app.tasks worker -l INFO -c 5 -Q low
```

**Test it:**
```bash
# Send email with priority
curl -X POST http://localhost:8000/tasks/email \
  -H "Content-Type: application/json" \
  -d '{"to":"user@example.com","subject":"Hello","body":"World","priority":"high"}'

# Generate report
curl -X POST http://localhost:8000/tasks/report \
  -H "Content-Type: application/json" \
  -d '{"report_id":123,"user_id":1,"report_type":"sales"}'

# Check task system health
curl http://localhost:8000/health/tasks
```

**Architecture:**
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ FastAPI (1)  │  │ FastAPI (2)  │  │ FastAPI (3)  │
│ API Only     │  │ API Only     │  │ API Only     │
└──────────────┘  └──────────────┘  └──────────────┘
         ↓                ↓                ↓
    ┌────────────────────────────────────────┐
    │              Redis Broker              │
    └────────────────────────────────────────┘
         ↑                ↑                ↑
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Worker (20)  │  │ Worker (10)  │  │ Worker (5)   │
│ High Queue   │  │ Normal Queue │  │ Low Queue    │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Pros:**
- ✅ Highly scalable
- ✅ Independent scaling of API and workers
- ✅ Better resource utilization
- ✅ Priority-based processing

**Cons:**
- ❌ More complex deployment
- ❌ Requires proper monitoring

### 3. Docker Deployment

**File:** `docker-compose.yml`

Complete production deployment with Docker Compose.

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale worker-normal=5

# Stop everything
docker-compose down
```

**What's included:**
- 🔴 Redis (message broker)
- 🌐 FastAPI API (4 workers)
- ⚡ High-priority workers (2 replicas, 20 concurrency)
- ⚙️ Normal-priority workers (3 replicas, 10 concurrency)
- 📊 Low-priority workers (1 replica, 5 concurrency)
- 🔍 Redis Commander (monitoring at http://localhost:8081)

**Services:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Redis Commander: http://localhost:8081
- Redis: localhost:6379

**Architecture:**
```
┌────────────────────────────────────────────┐
│           Docker Network                   │
│                                            │
│  ┌─────────┐                               │
│  │  Redis  │                               │
│  └────┬────┘                               │
│       │                                    │
│  ┌────┴────┐  ┌──────────┐  ┌──────────┐  │
│  │  API    │  │ Worker-H │  │ Worker-N │  │
│  │ (x4)    │  │ (x2,c20) │  │ (x3,c10) │  │
│  └─────────┘  └──────────┘  └──────────┘  │
│                                            │
└────────────────────────────────────────────┘
```

## 📚 Comparison Table

| Feature | Simple | Production | Docker |
|---------|--------|------------|--------|
| Setup Complexity | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| Scalability | Low | High | High |
| Resource Isolation | No | Yes | Yes |
| Priority Queues | No | Yes | Yes |
| Production Ready | No | Yes | Yes |
| Best For | Learning | Large apps | DevOps |

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO

# Worker Configuration
WORKER_CONCURRENCY=10
MAX_RETRIES=3
TASK_TTL=3600
```

### Worker Concurrency Guidelines

**CPU-bound tasks:**
```bash
# Set concurrency to number of CPU cores
aiotasks -A app.tasks worker -c 4
```

**I/O-bound tasks (network, database, file I/O):**
```bash
# Higher concurrency is fine
aiotasks -A app.tasks worker -c 20
```

**Mixed workload:**
```bash
# Use separate workers for different task types
aiotasks -A app.tasks worker -c 4 -Q cpu_tasks
aiotasks -A app.tasks worker -c 20 -Q io_tasks
```

## 📊 Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Task system health
curl http://localhost:8000/health/tasks

# Metrics
curl http://localhost:8000/metrics
```

### Redis Monitoring

```bash
# Monitor Redis
redis-cli MONITOR

# Check queue length
redis-cli LLEN aiotasks:tasks

# View all keys
redis-cli KEYS "*"
```

### Docker Monitoring

```bash
# View logs
docker-compose logs -f api
docker-compose logs -f worker-high
docker-compose logs -f worker-normal

# View stats
docker stats

# Inspect service
docker-compose ps
```

## 🐛 Troubleshooting

### Issue: Tasks Not Processing

**Symptoms:** Tasks are queued but never execute.

**Solutions:**
1. Check workers are running: `docker-compose ps` or `ps aux | grep aiotasks`
2. Verify Redis connection: `redis-cli ping`
3. Check worker logs: `docker-compose logs worker-normal`
4. Ensure workers use same broker URL as API

### Issue: Slow Task Processing

**Symptoms:** Tasks take too long to complete.

**Solutions:**
1. Increase worker concurrency: `-c 20` → `-c 50`
2. Add more workers: `docker-compose up -d --scale worker-normal=5`
3. Use priority queues for important tasks
4. Profile tasks to find bottlenecks

### Issue: High Memory Usage

**Symptoms:** Workers consuming too much memory.

**Solutions:**
1. Reduce concurrency: `-c 50` → `-c 20`
2. Set task TTL: `task_ttl=3600`
3. Restart workers periodically
4. Check for memory leaks in task code

### Issue: Connection Errors

**Symptoms:** `ConnectionError: Error connecting to Redis`

**Solutions:**
1. Check Redis is running: `docker ps | grep redis`
2. Verify REDIS_URL environment variable
3. Check network connectivity
4. Ensure Redis port (6379) is accessible

## 📖 Next Steps

1. **Read the documentation:** [FastAPI Integration Guide](../../docs/examples/fastapi.md)
2. **Explore task patterns:** [Advanced Patterns](../../docs/examples/advanced.md)
3. **Learn about retry logic:** [Retry & Error Handling](../../docs/guide/retry.md)
4. **Configure backends:** [Backends Guide](../../docs/guide/backends.md)

## 💡 Tips

### Development
- Use `memory://` broker for quick testing (no Redis needed)
- Enable auto-reload: `uvicorn app:api --reload`
- Use `LOG_LEVEL=DEBUG` for detailed logs

### Production
- Always use Redis or RabbitMQ (never `memory://`)
- Run multiple workers for reliability
- Monitor Redis memory usage
- Set appropriate task TTL
- Use separate workers for CPU vs I/O tasks
- Enable health checks in your orchestrator
- Set resource limits in Docker

### Performance
- Use `uvloop` (included by default with aiotasks)
- Enable `ujson` for faster JSON: `pip install aiotasks`
- Use connection pooling for Redis
- Profile your tasks to find bottlenecks
- Consider task priorities for mixed workloads

## 📄 License

These examples are part of the AioTasks project and are licensed under BSD-3-Clause.
