import logging

from .model import *
from ..helpers import *
from .api import run_default_aiotasks

log = logging.getLogger('aiotasks')


def launch_aiotasks_in_console(shared_config, **kwargs):
    """Launch in console mode"""
    
    # Load config
    config = AioTasksDefaultModel(**shared_config, **kwargs)
    
    # Check if config is valid
    if not config.is_valid:
        for prop, msg in config.validation_errors:
            log.critical("[!] '%s' property %s" % (prop, msg))
        return
    
    log.setLevel(config.verbosity)
    
    try:
        log.console("Starting aioTasks")
        
        run_default_aiotasks(config)
    
    except KeyboardInterrupt:
        log.console("[*] CTRL+C caught. Exiting...")
    except Exception as e:
        log.critical("[!] Unhandled exception: %s" % str(e))
        
        log.exception("[!] Unhandled exception: %s" % e, stack_info=True)
    finally:
        log.debug("[*] Shutdown...")
        

__all__ = ("launch_aiotasks_in_console",)
