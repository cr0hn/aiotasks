
from aiotasks import SharedConfig, String


class AioTasksDefaultModel(SharedConfig):
    application = String()
    log_level = String()
    config_file = String()
    
__all__ = ("AioTasksDefaultModel", )


