import re

_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


def parse_version(text: str | None) -> tuple | None:
    """Sort key for X.Y.Z[-pre]; a release sorts after its own prereleases."""
    match = _VERSION.match(text or "")
    if not match:
        return None
    major, minor, patch, pre = match.groups()
    if pre is None:
        pre_key = (1,)
    else:
        pre_key = (0, tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split(".")))
    return (int(major), int(minor), int(patch), pre_key)


def is_older(a: str | None, b: str | None) -> bool:
    pa, pb = parse_version(a), parse_version(b)
    if pa is None or pb is None:
        return False
    return pa < pb
