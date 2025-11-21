"""Core data models for aiotasks."""

from pydantic import BaseModel


class SharedConfig(BaseModel):
    """Shared configuration for aiotasks."""

    verbosity: int = 0
    timeout: int = 10
    debug: bool = False
