import logging

from aiotasks import AioTasksTypeError, SharedConfig

log = logging.getLogger('aiotasks')


def check_input_config(config: SharedConfig) -> None | AioTasksTypeError:
    if config and not config.is_valid:
        for prop, msg in config.validation_errors:
            raise AioTasksTypeError(f"'{prop}' property {msg}")

    return None


def run_with_exceptions_and_logs(function, config):
    try:
        log.console("Starting aioTasks")

        function(config)

    except KeyboardInterrupt:
        log.console("[*] CTRL+C caught. Exiting...")
    except Exception as e:
        log.critical(f"[!] Unhandled exception: {e}")

        if config.debug:
            log.exception(f"[!] Unhandled exception: {e}",
                          stack_info=True)
    finally:
        log.console("[*] Shutdown...")


__all__ = ("check_input_config", "run_with_exceptions_and_logs")
