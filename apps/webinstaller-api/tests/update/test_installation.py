import json
import os
import stat
from datetime import datetime

from update.installation import (
    BACKUP_DIR,
    COMPOSE,
    ENV,
    State,
    atomic_write,
    backup,
    load_state,
    read_header,
    save_state,
    strip_header,
    with_header,
)

NOW = datetime(2026, 11, 5, 9, 30, 0)


def test_header_roundtrip():
    assert read_header(with_header("x\n", "2.2.0")) == "2.2.0"
    assert strip_header(with_header("x\n", "2.2.0")) == "x\n"


def test_strip_header_without_header_is_unchanged():
    assert strip_header("services:\n") == "services:\n"
    assert read_header("services:\n") is None


def test_header_like_line_not_on_line_one_is_ignored():
    text = "services:\n# edulution-installer template 2.2.0\n"
    assert read_header(text) is None
    assert strip_header(text) == text


def test_load_state_missing(tmp_path):
    assert load_state(tmp_path) == State(None, [])


def test_state_roundtrip(tmp_path):
    save_state(tmp_path, State("2.2.0", ["a", "b"]))
    assert load_state(tmp_path) == State("2.2.0", ["a", "b"])
    data = json.loads((tmp_path / "edulution-update.json").read_text())
    assert data == {"templateVersion": "2.2.0", "applied": ["a", "b"]}


def test_atomic_write_keeps_mode(tmp_path):
    path = tmp_path / "f"
    path.write_text("old")
    path.chmod(0o600)
    atomic_write(path, "new")
    assert path.read_text() == "new"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert os.listdir(tmp_path) == ["f"]


def test_atomic_write_new_file_default_mode(tmp_path):
    path = tmp_path / "f"
    atomic_write(path, "x")
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    atomic_write(path, "y", mode=0o640)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_backup_names(tmp_path):
    (tmp_path / COMPOSE).write_bytes(b"compose\r\n")
    (tmp_path / ENV).write_bytes(b"A=1\n")
    first = backup(tmp_path, [COMPOSE, ENV, "missing"], NOW)
    assert [p.name for p in first] == [
        "docker-compose.yml.2026-11-05T09-30-00.backup",
        "edulution.env.2026-11-05T09-30-00.backup",
    ]
    assert first[0].parent == tmp_path / BACKUP_DIR
    second = backup(tmp_path, [COMPOSE], NOW)
    assert second[0].name == "docker-compose.yml.2026-11-05T09-30-00-1.backup"
    assert first[0].read_bytes() == b"compose\r\n"
    assert first[1].read_bytes() == b"A=1\n"
    assert stat.S_IMODE(first[1].stat().st_mode) == 0o600
