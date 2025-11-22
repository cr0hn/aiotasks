# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Python Requirement**: Now requires Python >=3.11
- **msgpack Compatibility**: Updated for msgpack 1.0+

### Fixed

- Circular import issues in actions/ modules
- Event loop handling in async contexts
