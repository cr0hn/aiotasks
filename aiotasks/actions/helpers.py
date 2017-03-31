import logging

from typing import Union

from aiotasks import SharedConfig, AioTasksTypeError

log = logging.getLogger('aiotasks')


def check_input_config(config: SharedConfig) -> Union[None, AioTasksTypeError]:
    if config and not config.is_valid:
        for prop, msg in config.validation_errors:
            raise AioTasksTypeError("'{}' property {}".format(prop, msg))

    return None


def run_with_exceptions_and_logs(function, config):
    try:
        log.console("Starting aioTasks")

        function(config)

    except KeyboardInterrupt:
        log.console("[*] CTRL+C caught. Exiting...")
    except Exception as e:
        log.critical("[!] Unhandled exception: {}".format(e))

        if config.debug:
            log.exception("[!] Unhandled exception: {}".format(e),
                          stack_info=True)
    finally:
        log.console("[*] Shutdown...")


__all__ = ("check_input_config", "run_with_exceptions_and_logs")
