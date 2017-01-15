import concurrent


class AioTasksError(Exception):
    pass


class AioTasksValueError(ValueError):
    pass


class AioTasksTypeError(TypeError):
    pass


class AioTasksTimeout(concurrent.futures.TimeoutError):
    pass


__all__ = ("AioTasksError", "AioTasksValueError", "AioTasksTypeError", "AioTasksTimeout")
