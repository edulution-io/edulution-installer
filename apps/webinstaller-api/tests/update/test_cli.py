import json

import pytest

from update.__main__ import main
from update.installation import COMPOSE, State, read_header
from update.templates import sha256

TARGET = "2.2.0"


@pytest.fixture(autouse=True)
def version(monkeypatch):
    monkeypatch.setenv("INSTALLER_VERSION", TARGET)


@pytest.fixture
def outdated(make_installation, target_text, monkeypatch, tmp_path):
    old = target_text.replace("edu-api", "edu-api-old", 1)
    root = make_installation(body=old, header="2.1.0", state=State("2.1.0", []))
    monkeypatch.setattr("update.__main__.history", lambda: frozenset({sha256(old)}))
    return root


def files(root):
    return {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}


def test_check_json_outdated(outdated, capsys):
    assert main(["--dir", str(outdated), "check", "--json"]) == 10
    assert json.loads(capsys.readouterr().out)["status"] == "outdated"


def test_check_human(outdated, capsys):
    assert main(["--dir", str(outdated), "check"]) == 10
    out = capsys.readouterr().out
    assert "2.1.0" in out and TARGET in out and "0001-mongo-replica-set-env" in out


def test_apply_without_yes(outdated, capsys):
    before = files(outdated)
    assert main(["--dir", str(outdated), "apply", "--expect", "x"]) == 2
    assert "Ohne --yes wird nichts geändert." in capsys.readouterr().err
    assert files(outdated) == before


def test_expect_then_apply(outdated, capsys):
    assert main(["--dir", str(outdated), "expect"]) == 0
    token = capsys.readouterr().out.strip()
    assert main(["--dir", str(outdated), "apply", "--yes", "--expect", token]) == 0
    assert TARGET in capsys.readouterr().out
    assert main(["--dir", str(outdated), "check"]) == 0


def test_error_code_passthrough(outdated, capsys):
    assert main(["--dir", str(outdated), "apply", "--yes", "--expect", "wrong"]) == 4
    assert capsys.readouterr().err.strip()


def test_migrate_accepts_discard_local_changes(outdated, capsys):
    argv = ["--dir", str(outdated), "migrate", "--id", "nope", "--yes", "--expect", "x"]
    assert main(argv + ["--discard-local-changes"]) == 2


def test_missing_files_exit_1(tmp_path, capsys):
    assert main(["--dir", str(tmp_path), "check"]) == 1
    captured = capsys.readouterr()
    assert captured.err.strip() and "Traceback" not in captured.out


def test_init(make_installation, target_text, capsys):
    root = make_installation(body=target_text)
    assert main(["--dir", str(root), "init"]) == 0
    assert read_header((root / COMPOSE).read_text()) == TARGET
    assert main(["--dir", str(root), "check"]) == 0
