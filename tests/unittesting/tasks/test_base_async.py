from aiotasks import build_manager


def test_build_manager_invalid_prefix(event_loop):
    import logging
    
    logger = logging.getLogger("aiotasks")
    
    class CustomLogger(logging.StreamHandler):
        def __init__(self):
            super(CustomLogger, self).__init__()
            self.content = []
        
        def emit(self, record):
            self.content.append(record.msg)
    
    custom = CustomLogger()
    logger.addHandler(custom)
    
    manager = build_manager(dsn="memory://", loop=event_loop, prefix=None)
    
    assert manager.task_prefix == "aiotasks"
    assert "Empty task_prefix. Using 'aiotasks' as task_prefix" in custom.content


def test_build_manager_invalid_prefix_type(event_loop):
    manager = build_manager(dsn="memory://", loop=event_loop, prefix=11)
    
    assert manager.task_prefix == "11"
