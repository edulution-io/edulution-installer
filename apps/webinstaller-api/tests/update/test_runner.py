import os
import stat

import pytest

from update.drift import check, exit_code, fingerprint
from update.envfile import EnvFile
from update.installation import BACKUP_DIR, COMPOSE, ENV, LOCK, State, load_state, read_header
from update.migrations import MIGRATIONS, Migration
from update.runner import UpdateError, apply, init, locked, migrate
from update.templates import sha256

TARGET = "2.2.0"
MONGO_ID = "0001-mongo-replica-set-env"


def snapshot(root):
    return {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}


def run_apply(root, target_text, history=frozenset(), expect=None, discard=False, **extra):
    return apply(
        root,
        expect=fingerprint(root) if expect is None else expect,
        discard_local_changes=discard,
        target_text=target_text,
        target_version=extra.pop("target_version", TARGET),
        history=history,
        **extra,
    )


@pytest.fixture
def outdated(make_installation, target_text):
    old = target_text.replace("edu-api", "edu-api-old", 1)
    root = make_installation(body=old, header="2.1.0", state=State("2.1.0", []))
    return root, frozenset({sha256(old)})


def test_apply_outdated(outdated, target_text):
    root, history = outdated
    report = run_apply(root, target_text, history)
    assert (root / COMPOSE).read_text() == f"# edulution-installer template {TARGET}\n{target_text}"
    env = EnvFile.parse((root / ENV).read_text())
    assert "replicaSet=rs0" in env.get("MONGODB_SERVER_URL")
    state = load_state(root)
    assert state.template_version == TARGET
    assert MONGO_ID in state.applied
    backups = sorted(p.name for p in (root / BACKUP_DIR).iterdir())
    assert any(n.startswith(COMPOSE) for n in backups)
    env_backup = next(p for p in (root / BACKUP_DIR).iterdir() if p.name.startswith(ENV))
    assert stat.S_IMODE(env_backup.stat().st_mode) == 0o600
    assert stat.S_IMODE((root / ENV).stat().st_mode) == 0o600
    assert exit_code(report) == 0


def test_apply_requires_matching_expect(outdated, target_text):
    root, history = outdated
    before = snapshot(root)
    with pytest.raises(UpdateError) as err:
        run_apply(root, target_text, history, expect="stale")
    assert err.value.code == 4
    assert_untouched_except_lock(root, before)


def assert_untouched_except_lock(root, before):
    after = snapshot(root)
    after.pop(LOCK, None)
    assert after == before
    assert not (root / BACKUP_DIR).exists()


def test_apply_modified_without_discard(make_installation, target_text):
    root = make_installation(body=target_text + "# local\n", header=TARGET, state=State(TARGET, []))
    before = snapshot(root)
    with pytest.raises(UpdateError) as err:
        run_apply(root, target_text)
    assert err.value.code == 20
    assert_untouched_except_lock(root, before)
    run_apply(root, target_text, discard=True)
    assert (root / COMPOSE).read_text().endswith(target_text)
    assert "# local" not in (root / COMPOSE).read_text()


def test_apply_refuses_downgrade(make_installation, target_text):
    root = make_installation(header="2.3.0", state=State("2.3.0", [m.id for m in MIGRATIONS]))
    before = snapshot(root)
    with pytest.raises(UpdateError) as err:
        run_apply(root, target_text)
    assert err.value.code == 5
    assert_untouched_except_lock(root, before)


GATE = Migration("0099-gate", "major", (), lambda c: True, lambda c: c.env.set_if_absent("GATED", "1"),
                 gates_template=True)


def test_apply_blocked(make_installation, target_text, all_applied):
    root = make_installation(header=TARGET, state=all_applied)
    before = snapshot(root)
    with pytest.raises(UpdateError) as err:
        run_apply(root, target_text, registry=(GATE,))
    assert err.value.code == 30
    assert_untouched_except_lock(root, before)


def test_lock_busy(outdated, target_text):
    root, history = outdated
    before = snapshot(root)
    with locked(root):
        with pytest.raises(UpdateError) as err:
            run_apply(root, target_text, history)
    assert err.value.code == 3
    assert_untouched_except_lock(root, before)


def test_lock_released_and_file_kept(tmp_path):
    with locked(tmp_path):
        pass
    assert (tmp_path / LOCK).exists()
    with locked(tmp_path):
        pass


def test_apply_twice_is_fixed_point(outdated, target_text):
    root, history = outdated
    run_apply(root, target_text, history)
    before = snapshot(root)
    backups = sorted(os.listdir(root / BACKUP_DIR))
    report = run_apply(root, target_text, history)
    assert exit_code(report) == 0
    assert snapshot(root) == before
    assert sorted(os.listdir(root / BACKUP_DIR)) == backups


def test_apply_missing_env_writes_nothing(outdated, target_text):
    root, history = outdated
    (root / ENV).unlink()
    before = snapshot(root)
    with pytest.raises(UpdateError) as err:
        run_apply(root, target_text, history)
    assert err.value.code == 1
    assert_untouched_except_lock(root, before)


def test_env_with_specials_survives(make_installation, target_text):
    password = 'p@ss?:%&"x'
    env = (
        "A=1\n"
        f"MONGODB_PASSWORD={password}\n"
        f"MONGODB_SERVER_URL=mongodb://root:{password}@edu-db:27017/\n"
    )
    root = make_installation(header="2.1.0", state=State("2.1.0", []), env=env)
    run_apply(root, target_text)
    after = EnvFile.parse((root / ENV).read_text())
    assert after.get("MONGODB_PASSWORD") == password
    assert after.get("MONGODB_SERVER_URL").startswith(f"mongodb://root:{password}@edu-db:27017/")
    assert f"MONGODB_PASSWORD={password}\n" in (root / ENV).read_text()


def run_migrate(root, mid, target_text, registry, **extra):
    return migrate(
        root, mid, expect=extra.pop("expect", fingerprint(root)), target_text=target_text,
        target_version=TARGET, history=frozenset(), registry=registry, **extra,
    )


def test_migrate_gating_major(make_installation, target_text, all_applied):
    root = make_installation(header="2.1.0", state=State("2.1.0", [m.id for m in MIGRATIONS]))
    registry = (*MIGRATIONS, GATE)
    assert check(root, target_text, TARGET, frozenset(), registry).blocked_by == [GATE]
    report = run_migrate(root, GATE.id, target_text, registry, discard_local_changes=True)
    assert EnvFile.parse((root / ENV).read_text()).get("GATED") == "1"
    state = load_state(root)
    assert GATE.id in state.applied and state.template_version == TARGET
    assert read_header((root / COMPOSE).read_text()) == TARGET
    assert report.blocked_by == []
    assert check(root, target_text, TARGET, frozenset(), registry).blocked_by == []


def test_migrate_gating_modified_without_discard(make_installation, target_text):
    root = make_installation(body=target_text + "# local\n", header=TARGET,
                             state=State(TARGET, [m.id for m in MIGRATIONS]))
    before = snapshot(root)
    with pytest.raises(UpdateError) as err:
        run_migrate(root, GATE.id, target_text, (*MIGRATIONS, GATE))
    assert err.value.code == 20
    assert_untouched_except_lock(root, before)


def test_migrate_rejects_missing_requires(make_installation, target_text, all_applied):
    dependent = Migration("0100-next", "major", (), lambda c: True, lambda c: None, requires=("0099-gate",))
    root = make_installation(header=TARGET, state=all_applied)
    before = snapshot(root)
    with pytest.raises(UpdateError) as err:
        run_migrate(root, "0100-next", target_text, (GATE, dependent))
    assert err.value.code == 2
    assert "0099-gate" in err.value.message
    assert_untouched_except_lock(root, before)


@pytest.mark.parametrize("mid", ["nope", MONGO_ID])
def test_migrate_unknown_or_normal(make_installation, target_text, all_applied, mid):
    root = make_installation(header=TARGET, state=all_applied)
    with pytest.raises(UpdateError) as err:
        run_migrate(root, mid, target_text, MIGRATIONS)
    assert err.value.code == 2


def test_migrate_already_applied(make_installation, target_text):
    root = make_installation(header=TARGET, state=State(TARGET, [m.id for m in MIGRATIONS] + [GATE.id]))
    with pytest.raises(UpdateError) as err:
        run_migrate(root, GATE.id, target_text, (*MIGRATIONS, GATE))
    assert err.value.code == 2


def test_init_marks_all_applied(make_installation, target_text):
    root = make_installation()
    init(root, target_version=TARGET)
    assert (root / COMPOSE).read_text() == f"# edulution-installer template {TARGET}\n{target_text}"
    state = load_state(root)
    assert state.applied == [m.id for m in MIGRATIONS]
    assert state.template_version == TARGET
    assert exit_code(check(root, target_text, TARGET, frozenset())) == 0
