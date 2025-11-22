"""Worker model using pydantic."""

from typing import Literal

from aiotasks.core.model import SharedConfig


class AioTasksDefaultModel(SharedConfig):
    """Default model for aiotasks worker."""

    application: str = ""
    log_level: str = "INFO"
    config_file: str = ""
    concurrency: int = 4
    pool: Literal["async", "thread", "process"] = "async"


__all__ = ("AioTasksDefaultModel",)
