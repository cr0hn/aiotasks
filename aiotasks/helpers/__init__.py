from urllib.parse import urlparse


def parse_dsn(dsn: str) -> tuple:
    """Get a DSN and return pased info as:

    >>> dsn="redis://user:password@127.0.0.1:6379/0"
    >>> parse_dsn(dsn)
    "user", "password", "127.0.0.1", 6379, "0"
    """
    _, host, db, _, _, _ = urlparse(dsn)
    
    # Get user / Pass
    if "@" in host:
        credentials, host = host.split("@", maxsplit=1)
    else:
        credentials = None

    user, password = None, None
    if credentials:
        _splitted_cred = credentials.split(":", maxsplit=1)
        
        if len(_splitted_cred) == 1:
            user = _splitted_cred[0]
            password = ""
        else:
            user, password = _splitted_cred
    
    if ":" in host:
        host, port = host.split(":")
        port = int(port)
    else:
        port = None
    
    if db.startswith("/"):
        db = db[1:]
    if not db:
        db = ""
    
    return user, password, host, port, db


__all__ = ("parse_dsn", )
