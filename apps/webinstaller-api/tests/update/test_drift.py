import os

import pytest

from update.drift import check, exit_code, fingerprint, to_json
from update.installation import State
from update.migrations import MIGRATIONS, Migration
from update.templates import sha256

TARGET = "2.2.0"


def run(root, target_text, history=frozenset(), registry=None):
    kwargs = {} if registry is None else {"registry": registry}
    return check(root, target_text, TARGET, history, **kwargs)


def test_current(make_installation, target_text, all_applied):
    root = make_installation(header=TARGET, state=all_applied)
    report = run(root, target_text)
    assert report.status == "current"
    assert report.header_current
    assert report.installed_version == TARGET
    assert report.diff == ""
    assert report.expect == fingerprint(root)
    assert exit_code(report) == 0


def test_header_only_behind(make_installation, target_text, all_applied):
    root = make_installation(header="2.1.0", state=all_applied)
    report = run(root, target_text)
    assert report.status == "current"
    assert not report.header_current
    assert report.installed_version == "2.1.0"
    assert exit_code(report) == 10


def test_outdated(make_installation, target_text, all_applied):
    old = target_text.replace("edu-api", "edu-api-old", 1)
    root = make_installation(body=old, header="2.1.0", state=all_applied)
    report = run(root, target_text, history=frozenset({sha256(old)}))
    assert report.status == "outdated"
    assert exit_code(report) == 10


def test_modified(make_installation, target_text, all_applied):
    edited = target_text + "# local edit\n"
    root = make_installation(body=edited, header=TARGET, state=all_applied)
    report = run(root, target_text)
    assert report.status == "modified"
    assert "-# local edit" in report.diff
    assert "docker-compose.yml (2.2.0)" in report.diff
    assert exit_code(report) == 20


def test_unknown(make_installation, target_text, all_applied):
    root = make_installation(body=target_text + "# local edit\n", state=all_applied)
    report = run(root, target_text)
    assert report.status == "unknown"
    assert report.installed_version == all_applied.template_version
    assert exit_code(report) == 20


def test_line_endings_count_as_differences(make_installation, target_text, all_applied):
    root = make_installation(body=target_text.replace("\n", "\r\n"), header=TARGET, state=all_applied)
    assert run(root, target_text).status == "modified"


def test_pending_migration_counts(make_installation, target_text):
    root = make_installation(header=TARGET)
    report = run(root, target_text)
    assert report.status == "current"
    assert report.installed_version == TARGET
    assert [m.id for m in report.pending]
    assert report.recreate == ["edu-db", "edu-api"]
    assert exit_code(report) == 10


def test_blocked(make_installation, target_text, all_applied):
    gate = Migration("0099-gate", "major", (), lambda c: True, lambda c: None, gates_template=True)
    root = make_installation(header=TARGET, state=all_applied)
    report = run(root, target_text, registry=(gate,))
    assert report.blocked_by == [gate]
    assert report.available_majors == [gate]
    assert exit_code(report) == 30


def test_check_never_writes(make_installation, target_text):
    root = make_installation(header=TARGET)

    def snapshot():
        return {
            str(p): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*"))
            if p.is_file()
        } | {"dirs": sorted(str(p) for p in root.rglob("*"))}

    before = snapshot()
    run(root, target_text)
    assert snapshot() == before


def test_fingerprint_missing_env(make_installation):
    root = make_installation(header=TARGET)
    os.unlink(root / "edulution.env")
    compose, env = fingerprint(root).split(":")
    assert env == "-"
    assert len(compose) == 64


def test_json_shape(make_installation, target_text):
    root = make_installation(header=TARGET)
    data = to_json(run(root, target_text))
    assert set(data) == {
        "exitCode", "status", "installedVersion", "targetVersion", "headerCurrent", "downgrade",
        "pendingMigrations", "blockedBy", "availableMajorMigrations", "recreate", "expect", "diff",
    }
    assert data["exitCode"] == 10  # the Mongo migration is pending
    assert data["headerCurrent"] is True
    assert data["downgrade"] is False
    assert data["pendingMigrations"][0]["recreate"] == ["edu-db", "edu-api"]
    assert set(data["pendingMigrations"][0]) == {"id", "kind", "recreate"}
    assert data["installedVersion"] == TARGET
    assert data["targetVersion"] == TARGET


def test_downgrade_by_header(make_installation, target_text, all_applied):
    root = make_installation(header="2.3.0", state=all_applied)
    assert exit_code(run(root, target_text)) == 5
    data = to_json(run(root, target_text))
    assert data["exitCode"] == 5
    assert data["downgrade"] is True


@pytest.mark.parametrize("header", [None, "2.1.0"])
def test_downgrade_by_state(make_installation, target_text, header):
    root = make_installation(header=header, state=State("2.3.0", [m.id for m in MIGRATIONS]))
    assert exit_code(run(root, target_text)) == 5


def test_downgrade_comes_first(make_installation, target_text):
    gate = Migration("0099-gate", "major", (), lambda c: True, lambda c: None, gates_template=True)
    root = make_installation(body=target_text + "# local\n", header="2.3.0", state=State("2.3.0", []))
    assert exit_code(run(root, target_text, registry=(*MIGRATIONS, gate))) == 5


IDLE = Migration("0001-idle", "normal", ("idle-svc",), lambda c: False, lambda c: None)
BUSY = Migration("0002-busy", "normal", ("busy-svc",), lambda c: c.env.get("A") == "1", lambda c: None)


def test_recreate_lists_only_needed_migrations(make_installation, target_text):
    root = make_installation(header=TARGET)
    report = run(root, target_text, registry=(IDLE, BUSY))
    assert [m.id for m in report.pending] == [IDLE.id, BUSY.id]
    assert report.recreate == ["busy-svc"]
    assert exit_code(report) == 10


def test_recreate_without_env_counts_as_needed(make_installation, target_text):
    root = make_installation(header=TARGET)
    os.unlink(root / "edulution.env")
    assert run(root, target_text, registry=(IDLE, BUSY)).recreate == ["idle-svc", "busy-svc"]


def test_json_major_ids(make_installation, target_text, all_applied):
    gate = Migration("0099-gate", "major", (), lambda c: True, lambda c: None, gates_template=True)
    later = Migration("0100-next", "major", (), lambda c: True, lambda c: None, requires=(gate.id,))
    root = make_installation(header=TARGET, state=all_applied)
    data = to_json(run(root, target_text, registry=(gate, later)))
    assert data["blockedBy"] == [gate.id]
    assert data["availableMajorMigrations"] == [gate.id]


def test_headerless_current_body(make_installation, target_text, all_applied):
    root = make_installation(state=all_applied)
    report = run(root, target_text)
    assert report.status == "current"
    assert not report.header_current
    assert exit_code(report) == 10
