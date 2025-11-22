# Celery Compatibility Implementation Status

## 🎯 Goal
Enable full interoperability between AioTasks and Celery workers, allowing:
1. AioTasks API → Celery workers (send tasks from AioTasks, process with Celery)
2. Celery API → AioTasks workers (send tasks from Celery, process with AioTasks)
3. Mixed worker pools (some Celery, some AioTasks)

## ✅ Completed Components

### 1. Celery Protocol v2 Implementation (`aiotasks/celery_compat.py`)
- ✅ Complete Celery Protocol v2 message serialization
- ✅ Message deserialization (properties, headers, body)
- ✅ Task ID generation (UUID4 compatible)
- ✅ JSON and msgpack serialization support
- ✅ Helper functions for encoding/decoding
- ✅ Message format detection

Functions implemented:
- `serialize_celery_message()` - Create Celery v2 message structure
- `deserialize_celery_message()` - Parse Celery v2 messages
- `encode_celery_task()` - Full message encoding for broker
- `decode_celery_task()` - Full message decoding from broker
- `is_celery_message()` - Auto-detect message format
- `generate_task_id()` - Celery-compatible UUID generation

### 2. Context Manager Updates (`aiotasks/tasks/context.py`)
- ✅ Added `celery_compat` parameter to `AsyncWaitContextManager.__init__()`
- ✅ Modified `build_delay_message()` to support dual-format serialization
- ✅ Auto-selects JSON (Celery) or msgpack (AioTasks) based on mode
- ✅ Imports Celery compatibility functions

### 3. Base Classes Updates (`aiotasks/tasks/bases.py`)
- ✅ Added `celery_compat` parameter to `AsyncTaskDelayBase.__init__()`
- ✅ Modified `task()` decorator to pass `celery_compat` to context
- ✅ Modified `add_task()` to pass `celery_compat` to context
- ✅ Added `_deserialize_task_message()` for auto-format detection
- ✅ Updated `listen_tasks()` to auto-detect and deserialize both formats
- ✅ Added JSON import for Celery message parsing

## 🚧 Pending Completion

### 4. Backend Integration
Need to add `celery_compat` parameter to all backends:

**Required changes in `aiotasks/tasks/backends.py`:**
```python
# All backend __init__ methods need celery_compat parameter:
- MemoryBackend.__init__(celery_compat=False)
- RedisBackend.__init__(celery_compat=False)
- AMQPBackend.__init__(celery_compat=False)
- ZMQBackend.__init__(celery_compat=False)
- build_manager(celery_compat=False)
```

**Required changes in `aiotasks/app.py`:**
```python
# AioTasks.__init__ needs celery_compat parameter:
def __init__(
    self,
    name: str = "aiotasks",
    *,
    broker: str = "memory://",
    pool: str = "async",
    celery_compat: bool = False,  # NEW
    **config: Any,
) -> None:
```

### 5. Documentation
- [ ] Comprehensive usage guide in `docs/celery_interop.md`
- [ ] Examples showing AioTasks → Celery
- [ ] Examples showing Celery → AioTasks
- [ ] Migration guide from pure Celery
- [ ] README.md feature highlight
- [ ] CHANGELOG.md entry

### 6. Examples
- [ ] `examples_new/celery_interop/aiotasks_to_celery.py`
- [ ] `examples_new/celery_interop/celery_to_aiotasks.py`
- [ ] `examples_new/celery_interop/mixed_workers.py`
- [ ] Docker Compose setup for testing

### 7. Testing
- [ ] Unit tests for `celery_compat.py`
- [ ] Integration tests with real Celery workers
- [ ] Round-trip tests (AioTasks → Celery → AioTasks)
- [ ] Performance comparison benchmarks

## 📋 Implementation Plan

### Phase 1: Complete Core Integration (Next)
1. Update all backends to accept `celery_compat`
2. Update `AioTasks` class to accept `celery_compat`
3. Ensure parameter propagation through entire stack
4. Basic smoke testing

### Phase 2: Documentation & Examples
1. Write comprehensive interoperability guide
2. Create working examples with Docker Compose
3. Update README with this major feature
4. Add to CHANGELOG as v2.3.0 feature

### Phase 3: Testing & Validation
1. Write unit tests for protocol conversion
2. Integration tests with Celery 5.x
3. Performance benchmarks
4. Edge case handling

## 🎯 Use Cases

### Use Case 1: Gradual Migration
```python
# Start: Pure Celery
from celery import Celery
app = Celery('myapp', broker='redis://localhost')

# Transition: Mixed workers
# - Keep Celery for heavy tasks
# - Add AioTasks workers for async tasks
from aiotasks import AioTasks
tasks = AioTasks('myapp', broker='redis://localhost', celery_compat=True)

# End: Pure AioTasks
# All workers migrated, full async/await benefits
```

### Use Case 2: FastAPI + Celery Workers
```python
# FastAPI app sends tasks
from aiotasks import AioTasks
tasks = AioTasks('api', broker='redis://localhost', celery_compat=True)

@tasks.task()
async def send_email(to: str):
    ...

# Existing Celery workers process them (no code changes needed!)
# celery -A worker_module worker
```

### Use Case 3: Best of Both Worlds
```python
# Use AioTasks for I/O-bound tasks
aio_tasks = AioTasks('async_tasks', pool='async', celery_compat=True)

# Use Celery for CPU-intensive tasks (existing workers)
# They share the same Redis broker and can process each other's tasks!
```

## 🔧 Technical Details

### Message Format Comparison

**AioTasks Native (msgpack):**
```python
{
    "task_id": "abc123",
    "function": "tasks.add",
    "args": [4, 5],
    "kwargs": {"debug": True}
}
```

**Celery Protocol v2 (JSON):**
```python
{
    "properties": {
        "correlation_id": "uuid-here",
        "content_type": "application/json",
        ...
    },
    "headers": {
        "task": "tasks.add",
        "id": "uuid-here",
        "lang": "py",
        ...
    },
    "body": {
        "args": [4, 5],
        "kwargs": {"debug": True}
    }
}
```

### Auto-Detection Logic
The system auto-detects message format:
1. Try parsing as JSON
2. Check for Celery v2 structure (properties/headers/body)
3. If not Celery, parse as msgpack (AioTasks)
4. Extract normalized task info (task_id, function, args, kwargs)

This allows mixed message formats in the same queue!

## 📚 References
- [Celery Protocol v2 Docs](https://docs.celeryq.dev/en/stable/internals/protocol.html)
- [Celery Task Messages](https://docs.celeryq.dev/en/stable/internals/protocol.html#version-2)
- [AioTasks Documentation](docs/)

---

**Status**: 🟡 In Progress
**Last Updated**: 2024-11-22
**Next Steps**: Complete backend integration and create examples
