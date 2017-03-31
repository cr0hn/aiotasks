import socket
import logging
import warnings
import platform
import datetime

from typing import List, Dict
from threading import current_thread

from aiotasks import get_log_level

from .model import *
from .api import find_manager
from ...core.exceptions import AioTasksTypeError
from ..helpers import check_input_config, run_with_exceptions_and_logs

log = logging.getLogger('aiotasks')


def make_summary(config: AioTasksDefaultModel,
                 tasks_available: List,
                 subscribers: dict) -> str:
    now = datetime.datetime.now()

    display_subscriptions = []
    for topic, clients in subscribers.items():
        display_subscriptions.append("'{}'".format(topic))

        for client in clients:
            display_subscriptions.append("   > {}".format(client.__name__))

    return """
 \033[1;37;40m--------------
--------------- aiotasks@{hostname} {version}
---- ***** ----
--- ******* --- {os}-{arch}-i386-64bit {date} {time}
-- ***   *** --
-- ***   *** -- [config]
-- ***   *** -- .> app:         {app_id}
-- ********* -- .> transport:   redis://localhost:6379//
-- ***   *** -- .> results:     redis://localhost:6379/
-- ***   *** -- .> concurrency: {concurrency} (asyncio)
 --------------\033[0;0m


[tasks]
{tasks}

[subscriptions]
{subscriptions}
""".format(hostname=socket.gethostname(),
           version="1.0.0-a1",
           os=platform.system(),
           arch=platform.release(),
           date=now.strftime("%Y-%m-%d"),
           time=now.strftime("%H:%M:%S"),
           app_id=hex(current_thread().ident),
           concurrency=config.concurrency,
           tasks="-  \n".join(tasks_available),
           subscriptions="\n".join(display_subscriptions))


def launch_aiotasks_worker_in_console(shared_config, **kwargs):
    """Launch in console mode"""

    # Load config
    config = AioTasksDefaultModel(**shared_config, **kwargs)

    # Check if config is valid
    try:
        check_input_config(config)
    except AioTasksTypeError as e:
        log.console(str(e))
        return

    log.setLevel(get_log_level(config.verbosity))

    # manager = run_with_exceptions_and_logs(find_manager, config)
    manager = find_manager(config)

    # Check DSN
    if manager.dsn.startswith("memory://"):
        warnings.warn("aiotasks cmd binary can't be used with 'memory://' "
                      "backend. Please choose other and try again")
        return

    try:
        manager.run()

        # --------------------------------------------------------------------------
        # Display summary. Cloned from Celery
        # --------------------------------------------------------------------------
        print(make_summary(config,
                           manager.task_available_tasks.keys(),
                           manager.topics_subscribers))

        manager.blocking_wait()
    finally:
        manager.stop()


__all__ = ("launch_aiotasks_worker_in_console",)
