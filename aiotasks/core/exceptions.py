"""Custom exceptions for aiotasks."""


class AioTasksError(Exception):
    """Base exception for all aiotasks errors."""


class AioTasksValueError(ValueError):
    """Raised when an invalid value is provided."""


class AioTasksTypeError(TypeError):
    """Raised when an incorrect type is provided."""


class AioTasksTimeout(TimeoutError):
    """Raised when a task execution exceeds the timeout limit."""


__all__ = ("AioTasksError", "AioTasksTimeout", "AioTasksTypeError", "AioTasksValueError")
