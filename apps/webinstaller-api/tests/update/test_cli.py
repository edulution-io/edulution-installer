import json

import pytest

from update.__main__ import main
from update.installation import COMPOSE, State, read_header
from update.migrations import MIGRATIONS, Migration
from update.templates import sha256

TARGET = "2.2.0"
MONGO = "0001-mongo-replica-set-env"


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
    out = capsys.readouterr()
    token = out.out.strip()
    assert out.out == token + "\n" and out.err == ""
    assert main(["--dir", str(outdated), "apply", "--yes", "--expect", token]) == 0
    assert TARGET in capsys.readouterr().out
    assert main(["--dir", str(outdated), "check"]) == 0


def test_error_code_passthrough(outdated, capsys):
    assert main(["--dir", str(outdated), "apply", "--yes", "--expect", "wrong"]) == 4
    assert capsys.readouterr().err.strip()


GATE = Migration("0099-gate", "major", ("edu-api",), lambda c: True,
                 lambda c: c.env.set_if_absent("GATED", "1"), gates_template=True)


def token(root, capsys):
    main(["--dir", str(root), "expect"])
    return capsys.readouterr().out.strip()


def test_apply_discard_local_changes_is_forwarded(outdated, capsys):
    (outdated / COMPOSE).write_text("# edulution-installer template 2.1.0\nlocal: edit\n")
    argv = ["--dir", str(outdated), "apply", "--yes", "--expect", token(outdated, capsys)]
    assert main(argv) == 20
    assert main([*argv, "--discard-local-changes"]) == 0
    assert read_header((outdated / COMPOSE).read_text()) == TARGET


@pytest.fixture
def gated(make_installation, target_text, monkeypatch):
    registry = (*MIGRATIONS, GATE)
    monkeypatch.setattr("update.__main__.MIGRATIONS", registry)
    old = target_text.replace("edu-api", "edu-api-old", 1)
    monkeypatch.setattr("update.__main__.history", lambda: frozenset({sha256(old)}))
    return make_installation(body=old, header="2.1.0", state=State("2.1.0", []))


def test_migrate_discard_local_changes_is_forwarded(gated, capsys):
    (gated / COMPOSE).write_text("# edulution-installer template 2.1.0\nlocal: edit\n")
    argv = ["--dir", str(gated), "migrate", "--id", GATE.id, "--yes", "--expect", token(gated, capsys)]
    assert main(argv) == 20
    assert main([*argv, "--discard-local-changes"]) == 0


def test_migrate_summary_names_non_installing_migration(make_installation, monkeypatch, capsys):
    data = Migration("0098-data", "major", ("edu-api",), lambda c: True,
                     lambda c: c.env.set_if_absent("NG", "1"))
    monkeypatch.setattr("update.__main__.MIGRATIONS", (*MIGRATIONS, data))
    root = make_installation(header="2.1.0", state=State("2.1.0", [MONGO]))
    argv = ["--dir", str(root), "migrate", "--id", data.id, "--yes", "--expect", token(root, capsys)]
    assert main(argv) == 10
    out = capsys.readouterr().out
    assert data.id in out and "edu-api" in out and "Vorlage" not in out and "Bereits aktuell" not in out


def test_migrate_summary_with_template(gated, capsys):
    argv = ["--dir", str(gated), "migrate", "--id", GATE.id, "--yes", "--expect", token(gated, capsys)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert f"Vorlage {TARGET} installiert." in out and GATE.id in out and MONGO in out


def test_apply_summary_outdated(outdated, capsys):
    assert main(["--dir", str(outdated), "apply", "--yes", "--expect", token(outdated, capsys)]) == 0
    out = capsys.readouterr().out
    assert f"Vorlage {TARGET} installiert." in out and MONGO in out and "Bereits aktuell" not in out


def test_apply_summary_noop(make_installation, target_text, all_applied, capsys):
    root = make_installation(header=TARGET, state=all_applied)
    assert main(["--dir", str(root), "apply", "--yes", "--expect", token(root, capsys)]) == 0
    out = capsys.readouterr().out
    assert out == "Bereits aktuell, nichts geändert.\n"


def test_expect_with_equals_form(outdated, capsys):
    assert main(["--dir", str(outdated), "apply", "--yes", "--expect=-:-"]) == 4
    assert "usage:" not in capsys.readouterr().err


def test_expect_equals_form_both_files_missing(tmp_path, capsys):
    assert main(["--dir", str(tmp_path), "apply", "--yes", "--expect=-:-"]) == 1
    err = capsys.readouterr().err
    assert err.strip() and "usage:" not in err


def test_usage_error_returns_2(capsys):
    assert main(["bogus"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "usage:" in captured.err


def test_help_returns_0(capsys):
    assert main(["--help"]) == 0
    assert "usage:" in capsys.readouterr().out


def test_status_is_german(outdated, capsys):
    main(["--dir", str(outdated), "check"])
    out = capsys.readouterr().out
    assert "Status: veraltet" in out and "outdated" not in out


def test_empty_exception_message_prints_type(outdated, monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError()
    monkeypatch.setattr("update.__main__.check", boom)
    assert main(["--dir", str(outdated), "check"]) == 1
    assert "RuntimeError" in capsys.readouterr().err


def test_missing_files_exit_1(tmp_path, capsys):
    assert main(["--dir", str(tmp_path), "check"]) == 1
    captured = capsys.readouterr()
    assert captured.err.strip() and "Traceback" not in captured.out


def test_init(make_installation, target_text, capsys):
    root = make_installation(body=target_text)
    assert main(["--dir", str(root), "init"]) == 0
    assert read_header((root / COMPOSE).read_text()) == TARGET
    assert main(["--dir", str(root), "check"]) == 0
