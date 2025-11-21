"""Worker model using pydantic."""

from aiotasks.core.model import SharedConfig


class AioTasksDefaultModel(SharedConfig):
    """Default model for aiotasks worker."""

    application: str = ""
    log_level: str = "INFO"
    config_file: str = ""
    concurrency: int = 4


__all__ = ("AioTasksDefaultModel",)
