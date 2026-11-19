import os
import re
import stat

from envtools import envValue, generateSecret, openPrivate


def test_env_value_single_quotes_plain():
    assert envValue("a&b") == "'a&b'"


def test_env_value_double_quotes_when_single_quote_inside():
    assert envValue("it's") == '"it\'s"'


def test_env_value_escapes_in_double_quotes():
    assert envValue('x\'"$\\') == '"x\'\\"\\$\\\\"'


def test_open_private_mode(tmp_path):
    path = tmp_path / "f"
    with openPrivate(path) as f:
        f.write("secret")
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600

    existing = tmp_path / "g"
    existing.write_text("old")
    os.chmod(existing, 0o644)
    with openPrivate(existing) as f:
        f.write("new")
    assert stat.S_IMODE(os.stat(existing).st_mode) == 0o600


def test_generate_secret_alphabet():
    value = generateSecret()
    assert len(value) == 32
    assert re.fullmatch(r"[A-Za-z0-9]+", value)
