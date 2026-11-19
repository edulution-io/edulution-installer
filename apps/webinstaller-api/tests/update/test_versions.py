from update.versions import is_older, parse_version


def test_order():
    assert is_older("2.1.0", "2.2.0")
    assert is_older("2.1.0-rc.2", "2.1.0")
    assert is_older("2.1.0-rc.2", "2.1.0-rc.10")
    assert not is_older("2.2.0", "2.1.0")
    assert not is_older("2.1.0", "2.1.0")


def test_unparseable():
    assert not is_older("dev", "2.1.0")
    assert not is_older(None, "2.1.0")
    assert not is_older("2.1.0", "dev")
    assert parse_version("dev") is None
    assert parse_version("2.1") is None
