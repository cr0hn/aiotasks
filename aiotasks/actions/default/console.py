import logging

from .model import *
from .api import run_default_aiotasks
from ..helpers import check_input_config
from ...core.exceptions import AioTasksTypeError

log = logging.getLogger('aiotasks')


def launch_aiotasks_in_console(shared_config, **kwargs):
    """Launch in console mode"""

    # Load config
    config = AioTasksDefaultModel(**shared_config, **kwargs)

    # Check if config is valid
    try:
        check_input_config(config)
    except AioTasksTypeError as e:
        log.console(str(e))
        return

    log.setLevel(config.verbosity)

    try:
        log.console("Starting aioTasks")

        run_default_aiotasks(config)

    except KeyboardInterrupt:
        log.console("[*] CTRL+C caught. Exiting...")
    except Exception as e:
        log.critical("[!] Unhandled exception: {}".format(e))

        log.exception("[!] Unhandled exception: {}".format(e), stack_info=True)
    finally:
        log.console("[*] Shutdown...")


__all__ = ("launch_aiotasks_in_console",)
