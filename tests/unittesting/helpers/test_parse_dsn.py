from aiotasks import parse_dsn


def test_parse_dsn_runs_ok():
    dsn = "redis://root:root@127.0.0.1"
    
    user, password, host, port, path = parse_dsn(dsn)
    
    assert user == "root"
    assert password == "root"
    assert host == "127.0.0.1"
    assert port is None
    assert path == ""


def test_parse_dsn_user_and_no_password():
    dsn = "redis://root@127.0.0.1:9999"
    
    user, password, host, port, path = parse_dsn(dsn)
    
    assert user == "root"
    assert password == ""
    assert host == "127.0.0.1"
    assert port == 9999
    assert path == ""


def test_parse_dsn_empty_password():
    dsn = "redis://root:@127.0.0.1:9999"
    
    user, password, host, port, path = parse_dsn(dsn)
    
    assert user == "root"
    assert password == ""
    assert host == "127.0.0.1"
    assert port == 9999
    assert path == ""


def test_parse_dsn_empty_valid_path():
    dsn = "redis://root:@127.0.0.1:9999/20"
    
    user, password, host, port, path = parse_dsn(dsn)
    
    assert user == "root"
    assert password == ""
    assert host == "127.0.0.1"
    assert port == 9999
    assert path == "20"


def test_parse_dsn_empty_long_path():
    dsn = "redis://root:@127.0.0.1:9999/20/aaa/bbb"
    
    user, password, host, port, path = parse_dsn(dsn)
    
    assert user == "root"
    assert password == ""
    assert host == "127.0.0.1"
    assert port == 9999
    assert path == "20/aaa/bbb"
