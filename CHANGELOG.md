# Changelog

All notable changes to this project will be documented in this file.

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
