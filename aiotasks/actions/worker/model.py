from aiotasks import SharedConfig, String, Integer


class AioTasksDefaultModel(SharedConfig):
    application = String()
    log_level = String()
    config_file = String()
    concurrency = Integer(default=4)


__all__ = ("AioTasksDefaultModel", )
