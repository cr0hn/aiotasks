---
name: Pool Support (Thread/Process)
about: Add Celery-like pool support for worker execution
title: '[FEATURE] Add pool support (async/thread/process) like Celery'
labels: enhancement, feature
assignees: ''
---

## 🎯 Feature Request

Add support for different execution pools (like Celery) to handle different types of workloads.

## 📊 Current Limitation

AioTasks currently only supports asyncio coroutine pools (`asyncio.create_task()`). This works great for I/O-bound async tasks, but has limitations:

- ❌ Not optimal for CPU-bound tasks (GIL blocking)
- ❌ Cannot execute synchronous (blocking) functions
- ❌ No way to isolate tasks in separate processes

## 💡 Proposed Solution

Add `--pool` parameter similar to Celery:

```bash
# Asyncio pool (default - current behavior)
aiotasks -A app worker --pool=async -c 10

# Thread pool (for blocking I/O)
aiotasks -A app worker --pool=thread -c 20

# Process pool (for CPU-intensive tasks)
aiotasks -A app worker --pool=process -c 4
```

## 🏗️ Implementation

### Python API

```python
app = AioTasks(
    "myapp",
    broker="redis://localhost",
    pool="async",      # async | thread | process
    concurrency=10,
)
```

### Per-task pool override (advanced)

```python
@app.task(pool="thread")
def blocking_task():  # Sync function OK in thread pool
    import time
    time.sleep(1)

@app.task(pool="process")
def cpu_intensive(n):  # CPU-bound task
    return sum(i*i for i in range(n))

@app.task()  # Uses global pool (async)
async def async_task():
    await asyncio.sleep(1)
```

## 📋 Pool Types

| Pool | Executor | Use Case | Example |
|------|----------|----------|---------|
| `async` | asyncio.create_task() | I/O-bound async tasks (default) | API calls, DB queries, file I/O |
| `thread` | ThreadPoolExecutor | Blocking I/O, sync libraries | Legacy sync code, blocking APIs |
| `process` | ProcessPoolExecutor | CPU-intensive tasks | Data processing, ML, calculations |

## 🔍 Implementation Checklist

- [ ] Add `pool` parameter to `AsyncTaskDelayBase.__init__()`
- [ ] Create executor factory (`_create_executor()`)
- [ ] Adapt `_function_runner()` to use executor
- [ ] Allow `def` functions (not just `async def`)
- [ ] Update CLI to accept `--pool` parameter
- [ ] Add tests for all pool types
- [ ] Verify serialization works with ProcessPoolExecutor
- [ ] Ensure ACK/NACK works cross-process
- [ ] Update documentation
- [ ] Add migration guide

## 📚 References

- [Celery Concurrency](https://docs.celeryq.dev/en/stable/userguide/workers.html#concurrency)
- [asyncio Executors](https://docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools)
- [WORKER_EXECUTION_ANALYSIS.md](../WORKER_EXECUTION_ANALYSIS.md)

## 🎯 Target Version

v2.3.0 (post v2.2.0 release)

## 💬 Discussion

This is a significant architectural change. Please review [WORKER_EXECUTION_ANALYSIS.md](../WORKER_EXECUTION_ANALYSIS.md) for detailed analysis and recommendations.

**Benefits:**
- ✅ More flexible (handle CPU-bound and blocking tasks)
- ✅ Celery-compatible API
- ✅ Better resource utilization

**Risks:**
- ⚠️ Breaking changes if not careful
- ⚠️ Complexity increase
- ⚠️ More testing needed

