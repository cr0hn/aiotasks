import logging

from typing import Union

from aiotasks import SharedConfig, AioTasksTypeError

log = logging.getLogger('aiotasks')


def check_input_config(config: SharedConfig) -> Union[None, AioTasksTypeError]:
    if not config.is_valid:
        for prop, msg in config.validation_errors:
            raise AioTasksTypeError("'{}' property {}".format(prop, msg))

    return None

__all__ = ("check_input_config", )
