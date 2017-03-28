import os
import importlib

from functools import partial

from aiotasks import AsyncTaskBase

from .model import *
from ...core.exceptions import AioTasksError

here = os.getcwd()
get_path = partial(os.path.join, here)


def find_manager(config: AioTasksDefaultModel) -> AsyncTaskBase:
    assert isinstance(config, AioTasksDefaultModel)

    _module = str(config.application)

    if _module.endswith(".py"):
        _module = _module.replace(".py", "")

    # Try to find AsyncTaskBase var
    app = importlib.import_module(_module)

    manager = None
    for v in dir(app):
        if v.startswith("_"):
            continue

        value = getattr(app, v)

        if isinstance(value, AsyncTaskBase):
            manager = value
            break

    if not manager:
        raise AioTasksError("Not found AsyncTaskBase subclass instance")

    return manager

__all__ = ("find_manager",)
