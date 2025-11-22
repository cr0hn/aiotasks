# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - TBD

### Added

#### Pool Support - Multiple Execution Strategies

**Major Feature**: Support for thread and process pools (Celery-like pool types)

AioTasks now supports multiple execution pool types, enabling you to choose the best execution strategy for your workload:

- **`async` pool** (default): asyncio coroutines - best for I/O-bound async tasks
- **`thread` pool**: ThreadPoolExecutor - best for blocking I/O and sync libraries
- **`process` pool**: ProcessPoolExecutor - best for CPU-intensive tasks (bypasses GIL)

**Python API**:
```python
# Async pool (default) - I/O-bound async tasks
app = AioTasks('myapp', broker='redis://localhost', pool='async')

@app.task()
async def fetch_data(url: str):
    await asyncio.sleep(1)
    return data

# Thread pool - blocking I/O, sync libraries
app = AioTasks('myapp', broker='redis://localhost', pool='thread', concurrency=20)

@app.task()
def blocking_io(file_path: str):
    import time
    time.sleep(1)  # Blocking call OK in thread pool
    return result

# Process pool - CPU-intensive tasks
app = AioTasks('myapp', broker='redis://localhost', pool='process', concurrency=4)

@app.task()
def cpu_intensive(n: int):
    return sum(i*i for i in range(n))  # True parallel execution
```

**CLI Support**:
```bash
# Async pool (default)
aiotasks -A app worker -c 10

# Thread pool for blocking tasks
aiotasks -A app worker --pool=thread -c 20

# Process pool for CPU-intensive tasks
aiotasks -A app worker --pool=process -c 4
```

**Why This Matters**:
- ✅ **CPU-Intensive Tasks**: Process pool bypasses the GIL for true parallel execution
- ✅ **Legacy Code**: Thread pool allows using sync functions (def) instead of requiring async def
- ✅ **Blocking Libraries**: Thread pool handles blocking I/O without blocking the event loop
- ✅ **Celery Compatibility**: Similar to Celery's `--pool` parameter (prefork, threads, solo)

**Implementation Details**:
- Automatic executor creation (ThreadPoolExecutor / ProcessPoolExecutor)
- Seamless integration with existing retry logic and ACK/NACK
- Proper resource cleanup (executor shutdown on worker stop)
- Full backward compatibility (async pool is default)

**Examples**:
- New example: `examples_new/pool_types_example.py`
- Demonstrates all three pool types
- Shows appropriate use cases for each

### Changed

- `AsyncTaskDelayBase.__init__()`: Added `pool` parameter
- `AioTasks.__init__()`: Added `pool` parameter
- `build_manager()`: Added `pool` parameter
- All backend classes: Added `pool` parameter support
- Worker CLI: Added `-P/--pool` parameter
- Worker model: Added `pool` field with validation

### Technical Notes

- Pool type validation: Only accepts "async", "thread", or "process"
- Thread pool: Uses `asyncio.run_in_executor()` with ThreadPoolExecutor
- Process pool: Uses `asyncio.run_in_executor()` with ProcessPoolExecutor
- Async pool: Direct coroutine execution with `asyncio.create_task()` (existing behavior)
- Function validation:
  - async pool: Requires `async def` functions
  - thread/process pools: Accepts both `def` and `async def` (with warning for async def)

## [2.2.0] - 2024-11-22

### ⚠️  BREAKING CHANGES

- **Python 3.12+ Required**: Updated minimum Python version from 3.11 to 3.12
- **Full Installation by Default**: `pip install aiotasks` now installs ALL features (Redis, AMQP, ZeroMQ, FastAPI, ujson, uvloop)

### Changed

#### Installation
- **Simplified Installation**: Single command installs everything
  - `pip install aiotasks` now includes all brokers (Redis, AMQP, ZeroMQ)
  - FastAPI integration included by default
  - Performance optimizations (uvloop, ujson) included by default
  - No more optional dependencies - everything is batteries-included!
  - Legacy `[all]` extra kept for compatibility (now empty)

#### Python Version
- **Requires Python >=3.12** (was >=3.11)
- Updated all documentation to reference Python 3.12+
- Updated CI/CD workflows to use Python 3.12
- Updated tooling configuration (ruff, mypy, pylint) for Python 3.12
- Removed Python 3.11 from test matrix
- Test matrix now: Python 3.12, 3.13 on Ubuntu, macOS, Windows

#### CI/CD
- **Concurrency Control**: Only one publish workflow can run at a time
  - Previous publish runs are automatically canceled when a new one starts
  - Prevents conflicting releases and race conditions

#### Documentation
- Updated README.md: Simplified installation section
- Updated all examples: Changed `aiotasks[...]` to `aiotasks`
- Updated FastAPI integration guide
- Updated 10+ documentation and example files

### Why These Changes?

**Simpler for Users**: No need to figure out which extras to install - everything works out of the box

**Better Developer Experience**: Install once, use all features

**Production Ready**: All production-critical dependencies (Redis, uvloop, etc.) included by default

**Modern Python**: Take advantage of Python 3.12+ features (type aliases, improved pattern matching, etc.)

### Migration Guide

#### From v2.1.0 to v2.2.0

**Installation**:
```bash
# Before (v2.1.0)
pip install aiotasks[redis,fastapi]

# After (v2.2.0) - everything included!
pip install aiotasks
```

**Python Version**:
- Ensure you're using Python 3.12 or higher
- Update your project's `requires-python` if needed

**Dependencies**:
- All optional dependencies are now included
- Remove any `aiotasks[...]` references from requirements.txt
- Simply use `aiotasks` everywhere

## [2.1.0] - 2024-11-22

### Added

#### Installation & Dependencies
- **Broker-Specific Installation**: Optional dependencies by broker type for leaner installations
  - `pip install aiotasks[redis]` - Redis backend with hiredis optimization
  - `pip install aiotasks[amqp]` - RabbitMQ/AMQP backend (aio-pika)
  - `pip install aiotasks[zeromq]` - ZeroMQ backend (pyzmq)
  - `pip install aiotasks[fastapi]` - FastAPI + uvicorn integration
  - `pip install aiotasks[performance]` - ujson for faster JSON serialization
  - `pip install aiotasks[all]` - All features and backends included
- **uvloop by Default**: High-performance event loop (uvloop) now included in base installation for improved performance

#### Documentation
- **Comprehensive FastAPI Integration Guide** (`docs/examples/fastapi.md`, ~500 lines)
  - Quick start with step-by-step instructions
  - Three architecture patterns with pros/cons:
    - Pattern 1: Separate workers (production-recommended)
    - Pattern 2: In-process with threading (development)
    - Pattern 3: Hybrid approach (quick + heavy tasks)
  - Advanced examples: error handling, priority queues, task chaining, result retrieval
  - Production configuration best practices
  - Docker Compose deployment example
  - Performance tuning guidelines
  - Comprehensive troubleshooting section
  - Monitoring and health checks

- **Enhanced Installation Documentation**
  - Detailed comparison table showing what each installation option includes
  - Clear broker selection guide
  - Performance optimization recommendations
  - Memory backend vs Redis vs RabbitMQ vs ZeroMQ comparison

#### Examples
- **Complete FastAPI Integration Examples** (`examples_new/fastapi/`)
  - `simple_integration.py`: Recommended pattern - API queues tasks, workers run separately
  - `simple_integration_threaded.py`: Development pattern using threading.Thread for in-process workers
  - `production_app.py`: Production-ready app with:
    - Priority queues (high, normal, low)
    - Pydantic models for validation
    - Environment-based configuration
    - Health checks and metrics endpoints
    - Comprehensive logging
  - `docker-compose.yml`: Complete production deployment with:
    - Redis broker
    - FastAPI API (4 workers)
    - Separate task workers by priority (high: 2×20, normal: 3×10, low: 1×5)
    - Redis Commander for monitoring
  - `Dockerfile`: Production-ready container with security best practices
  - `requirements.txt`: Example dependencies
  - `README.md`: Comprehensive guide (400+ lines) with:
    - Architecture diagrams
    - Comparison of all patterns
    - Configuration examples
    - Troubleshooting guide
    - Performance tips

#### CI/CD
- **Enhanced Publish Workflow** (`.github/workflows/publish.yml`)
  - Manual trigger with explicit inputs:
    - `version`: Version to publish (e.g., 2.1.0)
    - `tag`: Git tag to create (e.g., v2.1.0)
    - `test_pypi`: Optional TestPyPI publishing
  - Automated version management:
    - Updates `pyproject.toml` with specified version
    - Commits version bump
    - Creates and pushes git tag
  - Multi-stage pipeline:
    1. Update version and create tag
    2. Build distribution from tag
    3. Publish to PyPI (production) or TestPyPI (testing)
    4. Create GitHub Release automatically
  - Improved safety with separate environments for PyPI and TestPyPI

### Changed

- **README.md**: Restructured installation section
  - Added "Choose Your Broker" subsection
  - Installation options table with feature matrix
  - Updated FastAPI integration example to show recommended pattern (separate workers)
  - Added alternative threading pattern for development
  - Clear warnings about production vs development patterns

- **Documentation Navigation**: Added "FastAPI Integration" to mkdocs.yml examples section

### Fixed

- **FastAPI Integration Anti-Pattern**: Removed and corrected incorrect worker initialization examples
  - **Problem**: Previous examples incorrectly called `tasks.run()` directly in `@api.on_event("startup")` async handlers
  - **Why it's wrong**: `tasks.run()` manages the event loop and blocks, causing conflicts when called in async context
  - **Solution**:
    - Recommended: Run workers in separate processes (production pattern)
    - Alternative: Use `threading.Thread` for in-process workers (development only)
  - **Files corrected**:
    - `README.md`: Updated FastAPI example
    - `docs/examples/fastapi.md`: Added clear warnings and correct patterns
    - `examples_new/fastapi/simple_integration.py`: Removed startup handlers, API only queues tasks
    - `examples_new/fastapi/simple_integration_threaded.py`: NEW - Shows correct threading pattern
    - `examples_new/fastapi/README.md`: Updated with pattern comparison

### Documentation Improvements

- **README.md**:
  - Broker-specific installation table with feature matrix
  - Enhanced FastAPI integration section with:
    - Recommended pattern (separate workers)
    - Alternative pattern (threading for development)
    - Clear execution instructions for both patterns
  - Visual separation between development and production approaches

- **docs/examples/fastapi.md**:
  - Warning banners about not calling `.run()` in async context
  - Three complete architecture patterns with code examples
  - Advanced integration examples
  - Docker Compose production setup
  - Performance optimization guide
  - Troubleshooting common issues

- **examples_new/fastapi/README.md**:
  - Comparison table of all integration approaches
  - ASCII architecture diagrams for each pattern
  - Step-by-step setup instructions
  - Configuration best practices (development vs production)
  - Docker deployment guide
  - Monitoring and health check examples

## [2.0.0] - 2024-01-XX

### Added

- **Celery-Style API**: New AioTasks class with familiar Celery-like interface
- **Modern Python 3.11+ Support**: Pattern matching, StrEnum, modern type hints
- **Retry Logic**: Automatic retry with exponential backoff using tenacity
- **ACK/NACK Support**: Task acknowledgment for reliable processing
- **TTL (Time-To-Live)**: Configurable task expiration
- **Comprehensive Testing**: Modern pytest test suite (40%+ coverage baseline)
- **CI/CD Pipeline**: GitHub Actions workflows for testing and deployment
- **Documentation**: MkDocs-based docs with multi-language support

### Changed

- **Pydantic Migration**: Migrated from deprecated booby to pydantic
- **Python Requirement**: Now requires Python >=3.12
- **msgpack Compatibility**: Updated for msgpack 1.0+

### Fixed

- Circular import issues in actions/ modules
- Event loop handling in async contexts
