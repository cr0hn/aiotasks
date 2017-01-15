import time
import socket
import inspect
import os.path
import subprocess

import redis
import pytest
import redislite


@pytest.fixture(scope="session")
def redis_instance():
    """
    This fixture ensures that a Redis instance is launched and yield the DSN to connecto to it
    """
    
    host = "127.0.0.1"
    port = "6379"
    
    # Is an Redis server launched?
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sock.connect_ex((host, int(port))) == 0:
        yield "redis://{}:{}".format(host, port)
    
    # NO Redis server found. Launch and instance
    else:
        redis_bin = os.path.join(os.path.dirname(inspect.getfile(redislite)), "bin", "redis-server")
        
        # Launch Redis server
        p = subprocess.Popen([redis_bin,
                              "--port", port,
                              "--bind", host])
        
        r = redis.Redis(host=host, port=int(port))
        
        # Wait until redis is available
        while True:
            if r.ping():
                break
            time.sleep(0.5)
        
        del r
        
        yield "redis://{}:{}".format(host, port)

        p.kill()
