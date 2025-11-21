import importlib
import os
import sys
from functools import partial

from aiotasks import AsyncTaskBase

from ...core.exceptions import AioTasksError
from .model import *

here = os.getcwd()
get_path = partial(os.path.join, here)


def find_manager(config: AioTasksDefaultModel) -> AsyncTaskBase:
    assert isinstance(config, AioTasksDefaultModel)

    _module = str(config.application)

    if _module.endswith(".py"):
        _module = _module.replace(".py", "")

    # Try to find AsyncTaskBase var
    try:
        app = importlib.import_module(_module)
    except ImportError:
        _module_with_extension = f"{_module}.py"

        # If import fails, try lo add the container folder to the path
        if os.path.exists(os.path.join(os.getcwd(), _module_with_extension)):
            _import_path = os.getcwd()
            _module = _module.replace("/", ".")

        elif os.path.exists(_module_with_extension):
            _pkg = os.path.dirname(os.path.abspath(_module_with_extension))

            if _pkg.startswith("/"):
                _pkg = _pkg[1:]

            _import_path = _pkg
            _module = _module.replace("/", ".")

        else:
            raise ValueError("Can't determinate module location")

        sys.path.append(_import_path)

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
