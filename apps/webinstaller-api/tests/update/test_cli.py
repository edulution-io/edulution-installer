import json

import pytest

from update.__main__ import RESOLVED_CONFIG_ENV, main
from update.installation import COMPOSE, LOCK, State, read_header
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


def test_check_human_names_an_outdated_header(make_installation, all_applied, capsys):
    root = make_installation(header="2.1.0", state=all_applied)
    assert main(["--dir", str(root), "check"]) == 10
    assert f"Versionskennung in docker-compose.yml wird auf {TARGET} gesetzt" in capsys.readouterr().out


def test_check_restart_pending(make_installation, target_text, all_applied, capsys):
    root = make_installation(header=TARGET, state=all_applied)
    assert main(["--dir", str(root), "check", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["restartPending"] is False
    assert main(["--dir", str(root), "check", "--json", "--restart-pending"]) == 10
    data = json.loads(capsys.readouterr().out)
    assert data["restartPending"] is True and data["exitCode"] == 10 and data["status"] == "current"
    assert main(["--dir", str(root), "check", "--restart-pending"]) == 10
    assert "Neustart der Dienste" in capsys.readouterr().out


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
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert data.id in out and "edu-api" in out and "Vorlage" not in out and "Bereits aktuell" not in out
    assert "Ein Update der Installation steht noch aus." in out


def test_migrate_in_gating_chain_exits_0_and_names_the_next(make_installation, monkeypatch, capsys):
    first = Migration("0098-a", "major", (), lambda c: True, lambda c: c.env.set_if_absent("A98", "1"),
                      gates_template=True)
    second = Migration("0099-b", "major", (), lambda c: True, lambda c: None, gates_template=True)
    monkeypatch.setattr("update.__main__.MIGRATIONS", (*MIGRATIONS, first, second))
    root = make_installation(header="2.1.0", state=State("2.1.0", [MONGO]))
    argv = ["--dir", str(root), "migrate", "--id", first.id, "--yes", "--expect", token(root, capsys)]
    assert main(argv) == 0
    assert "Weitere Migration nötig: 0099-b" in capsys.readouterr().out


def test_check_reports_downgrade(make_installation, all_applied, capsys):
    root = make_installation(header="2.3.0", state=all_applied)
    assert main(["--dir", str(root), "check"]) == 5


def test_migrate_summary_with_template(gated, capsys):
    argv = ["--dir", str(gated), "migrate", "--id", GATE.id, "--yes", "--expect", token(gated, capsys)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert f"Vorlage {TARGET} installiert." in out and GATE.id in out and MONGO in out
    assert "Weitere Migration" not in out and "steht noch aus" not in out


def test_apply_summary_outdated(outdated, capsys):
    assert main(["--dir", str(outdated), "apply", "--yes", "--expect", token(outdated, capsys)]) == 0
    out = capsys.readouterr().out
    assert f"Vorlage {TARGET} installiert." in out and MONGO in out and "Bereits aktuell" not in out


def test_apply_summary_skips_services_of_unneeded_migrations(outdated, capsys):
    (outdated / "edulution.env").write_text(
        "MONGODB_USERNAME=root\nMONGODB_PASSWORD=pw\nMONGODB_AUTH_SOURCE=admin\n"
        "MONGODB_SERVER_URL='mongodb://root:pw@edu-db:27017/?replicaSet=rs0&directConnection=true'\n"
    )
    main(["--dir", str(outdated), "check"])
    assert "Neu zu erstellende Dienste" not in capsys.readouterr().out
    assert main(["--dir", str(outdated), "apply", "--yes", "--expect", token(outdated, capsys)]) == 0
    out = capsys.readouterr().out
    assert MONGO in out and "Neu zu erstellende Dienste" not in out


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
    out = capsys.readouterr().out
    assert "usage:" in out
    assert "Frische Installation markieren (nur für den Installer)" in out


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


def test_check_names_missing_db_user(make_installation, capsys):
    root = make_installation(header="2.1.0", state=State("2.1.0", []), env="MONGODB_PASSWORD=pw\n")
    assert main(["--dir", str(root), "check"]) == 6
    assert "Blockiert: edu-api erhält MONGODB_USERNAME und MONGODB_PASSWORD" in capsys.readouterr().out
    assert main(["--dir", str(root), "check", "--restart-pending"]) == 6
    capsys.readouterr()
    before = files(root)
    token = main(["--dir", str(root), "expect"]) or capsys.readouterr().out.strip()
    assert main(["--dir", str(root), "apply", "--yes", "--expect", token]) == 6
    assert "Datenbank-Benutzer" in capsys.readouterr().err
    after = files(root)
    after.pop(LOCK, None)
    assert after == before


def resolved_config(tmp_path, monkeypatch, environment):
    path = tmp_path / "compose-config.json"
    path.write_text(json.dumps({"services": {"edu-api": {"environment": environment}}}))
    monkeypatch.setenv(RESOLVED_CONFIG_ENV, str(path))


def test_check_takes_edu_api_environment_from_compose(make_installation, tmp_path, monkeypatch, capsys):
    root = make_installation(header="2.1.0", state=State("2.1.0", []), env="MONGODB_PASSWORD=pw\n")
    # From docker-compose.override.yml, which edulution.env does not show.
    resolved_config(tmp_path, monkeypatch, {"MONGODB_USERNAME": "root", "MONGODB_PASSWORD": "pw"})
    assert main(["--dir", str(root), "check"]) == 10
    capsys.readouterr()


def test_check_takes_blanked_values_from_compose(make_installation, tmp_path, monkeypatch, capsys):
    # edulution.env has both, so only the resolved config can make the check fail.
    root = make_installation(
        header="2.1.0", state=State("2.1.0", []), env="MONGODB_USERNAME=root\nMONGODB_PASSWORD=pw\n"
    )
    assert main(["--dir", str(root), "check"]) == 10
    # ${MONGO_USER:-} that Compose resolved to empty.
    resolved_config(tmp_path, monkeypatch, {"MONGODB_USERNAME": "", "MONGODB_PASSWORD": "pw"})
    assert main(["--dir", str(root), "check"]) == 6
    # A bare "- MONGODB_USERNAME" without a value in the host environment.
    resolved_config(tmp_path, monkeypatch, {"MONGODB_USERNAME": None, "MONGODB_PASSWORD": "pw"})
    assert main(["--dir", str(root), "check"]) == 6
    capsys.readouterr()


def test_check_without_usable_resolved_config_reads_the_env_file(make_installation, tmp_path, monkeypatch, capsys):
    root = make_installation(header="2.1.0", state=State("2.1.0", []))
    broken = tmp_path / "broken.json"
    broken.write_text("{")
    monkeypatch.setenv(RESOLVED_CONFIG_ENV, str(broken))
    assert main(["--dir", str(root), "check"]) == 10
    no_service = tmp_path / "other.json"
    no_service.write_text(json.dumps({"services": {"edu-db": {}}}))
    monkeypatch.setenv(RESOLVED_CONFIG_ENV, str(no_service))
    assert main(["--dir", str(root), "check"]) == 10
    monkeypatch.setenv(RESOLVED_CONFIG_ENV, str(tmp_path / "missing.json"))
    assert main(["--dir", str(root), "check"]) == 10
    capsys.readouterr()


def test_apply_takes_edu_api_environment_from_compose(make_installation, tmp_path, monkeypatch, capsys):
    root = make_installation(header="2.1.0", state=State("2.1.0", []), env="MONGODB_PASSWORD=pw\n")
    resolved_config(tmp_path, monkeypatch, ["MONGODB_USERNAME=root", "MONGODB_PASSWORD=pw"])
    main(["--dir", str(root), "expect"])
    token = capsys.readouterr().out.strip()
    assert main(["--dir", str(root), "apply", "--yes", "--expect", token]) == 0
    capsys.readouterr()


def test_header_only_update_without_db_user_is_refused_before_writing(make_installation, all_applied, capsys):
    # Apart from the header the files are current; apply would write it, and the restart would follow.
    root = make_installation(header="2.1.0", state=all_applied, env="MONGODB_PASSWORD=pw\n")
    assert main(["--dir", str(root), "check"]) == 6
    before = files(root)
    main(["--dir", str(root), "expect"])
    token = capsys.readouterr().out.strip()
    assert main(["--dir", str(root), "apply", "--yes", "--expect", token]) == 6
    after = files(root)
    after.pop(LOCK, None)
    assert after == before
    capsys.readouterr()


def test_restart_check_reads_the_installed_files(make_installation, target_text, capsys):
    # Files an older release wrote, whatever this release's template holds.
    root = make_installation(header="2.1.0", state=State("2.1.0", []), env="MONGODB_PASSWORD=pw\n")
    assert main(["--dir", str(root), "restart-check"]) == 6
    assert "Blockiert: edu-api erhält MONGODB_USERNAME" in capsys.readouterr().out
    plain = make_installation(body=target_text.replace("--keyFile", "--bind_ip_all"), env="MONGODB_PASSWORD=pw\n")
    assert main(["--dir", str(plain), "restart-check"]) == 0


def test_restart_check_takes_edu_api_environment_from_compose(make_installation, tmp_path, monkeypatch, capsys):
    root = make_installation(header="2.1.0", state=State("2.1.0", []), env="MONGODB_PASSWORD=pw\n")
    resolved_config(tmp_path, monkeypatch, {"MONGODB_USERNAME": "root", "MONGODB_PASSWORD": "pw"})
    assert main(["--dir", str(root), "restart-check"]) == 0
    resolved_config(tmp_path, monkeypatch, {"MONGODB_USERNAME": "", "MONGODB_PASSWORD": "pw"})
    assert main(["--dir", str(root), "restart-check"]) == 6
    capsys.readouterr()


def test_restart_check_writes_nothing(make_installation, capsys):
    root = make_installation(header="2.1.0", state=State("2.1.0", []), env="MONGODB_PASSWORD=pw\n")
    before = files(root)
    main(["--dir", str(root), "restart-check"])
    assert files(root) == before
    capsys.readouterr()
