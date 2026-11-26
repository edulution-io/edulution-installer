from activity import IdleWatch


def test_expires_after_the_limit_without_use():
    idle = IdleWatch(limit=100)
    # Whole seconds off the limit: start + 100 - start is not always 100 in floating point.
    assert not idle.expired(now=idle.last + 99)
    assert idle.expired(now=idle.last + 101)


def test_use_restarts_the_limit():
    idle = IdleWatch(limit=100)
    idle.last -= 99
    idle.touch()
    assert not idle.expired(now=idle.last + 99)
