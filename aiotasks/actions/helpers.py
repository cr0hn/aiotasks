import logging

from aiotasks.core.exceptions import AioTasksTypeError
from aiotasks.core.model import SharedConfig

log = logging.getLogger("aiotasks")


def check_input_config(config: SharedConfig) -> None | AioTasksTypeError:  # noqa: ARG001
    # Pydantic validates the config during construction, so no additional
    # validation is needed here. This function is kept for backwards compatibility.
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
            log.exception(f"[!] Unhandled exception: {e}", stack_info=True)
    finally:
        log.console("[*] Shutdown...")


__all__ = ("check_input_config", "run_with_exceptions_and_logs")
