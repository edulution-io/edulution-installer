import pytest

from update.envfile import EnvFile
from update.installation import State
from update.migrations import (
    MIGRATIONS,
    Context,
    Migration,
    available_majors,
    blocking_majors,
    pending_normal,
)
from update.migrations.m0001_mongo_replica_set import MIGRATION, with_replica_set

BASE = "mongodb://root:pw@edu-db:27017/"
WANTED = "?replicaSet=rs0&directConnection=true"


def test_with_replica_set_adds_params():
    assert with_replica_set(BASE) == BASE + WANTED


@pytest.mark.parametrize("password", ["p@ss", "a:b%2F&c", "x?y"])
def test_with_replica_set_keeps_password(password):
    prefix = f"mongodb://root:{password}@"
    result = with_replica_set(prefix + "edu-db:27017/")
    assert result.startswith(prefix)
    assert result == prefix + "edu-db:27017/" + WANTED


def test_with_replica_set_keeps_other_params():
    assert with_replica_set(BASE + "?authSource=admin") == (
        BASE + "?authSource=admin&replicaSet=rs0&directConnection=true"
    )


def test_with_replica_set_corrects_existing_value():
    assert with_replica_set(BASE + "?replicaSet=foo&x=1") == (
        BASE + "?replicaSet=rs0&x=1&directConnection=true"
    )


def test_with_replica_set_without_at():
    assert with_replica_set("mongodb://edu-db:27017") == "mongodb://edu-db:27017" + WANTED


def test_with_replica_set_is_fixed_point():
    once = with_replica_set(BASE)
    assert with_replica_set(once) == once


def test_migration_on_pre_july_env(tmp_path):
    env = EnvFile.parse(
        "A=1\nMONGODB_PASSWORD=pw\nMONGODB_SERVER_URL=mongodb://root:pw@edu-db:27017/\nB=2\n"
    )
    ctx = Context(tmp_path, env)
    assert MIGRATION.needed(ctx)
    MIGRATION.apply(ctx)
    assert env.get("MONGODB_AUTH_SOURCE") == "admin"
    lines = env.render().split("\n")
    assert lines[lines.index("MONGODB_PASSWORD=pw") + 1] .startswith("MONGODB_AUTH_SOURCE=")
    assert env.get("MONGODB_SERVER_URL") == BASE + WANTED
    assert not MIGRATION.needed(ctx)
    before = env.render()
    MIGRATION.apply(ctx)
    assert env.render() == before


def test_migration_url_with_inline_comment(tmp_path):
    env = EnvFile.parse(f"MONGODB_AUTH_SOURCE=admin\nMONGODB_SERVER_URL={BASE} # set by hand\n")
    MIGRATION.apply(Context(tmp_path, env))
    assert env.get("MONGODB_SERVER_URL") == BASE + WANTED


def test_migration_keeps_interpolation(tmp_path):
    env = EnvFile.parse(
        "MONGODB_AUTH_SOURCE=admin\n"
        "MONGODB_SERVER_URL=mongodb://root:${MONGODB_PASSWORD}@edu-db:27017/\n"
    )
    MIGRATION.apply(Context(tmp_path, env))
    assert env.render().endswith(
        "MONGODB_SERVER_URL=mongodb://root:${MONGODB_PASSWORD}@edu-db:27017/" + WANTED + "\n"
    )


def test_migration_updates_the_effective_url(tmp_path):
    env = EnvFile.parse(f"MONGODB_AUTH_SOURCE=admin\nMONGODB_SERVER_URL=old\nMONGODB_SERVER_URL='{BASE}'\n")
    ctx = Context(tmp_path, env)
    assert MIGRATION.needed(ctx)
    MIGRATION.apply(ctx)
    assert env.render() == f"MONGODB_AUTH_SOURCE=admin\nMONGODB_SERVER_URL=old\nMONGODB_SERVER_URL='{BASE}{WANTED}'\n"
    assert not MIGRATION.needed(ctx)


def test_migration_on_current_env(tmp_path):
    env = EnvFile.parse(
        "MONGODB_PASSWORD=pw\n"
        "MONGODB_AUTH_SOURCE=admin\n"
        'MONGODB_SERVER_URL="mongodb://root:pw@edu-db:27017/?replicaSet=rs0&directConnection=true"\n'
    )
    assert not MIGRATION.needed(Context(tmp_path, env))


def test_registry_is_sorted():
    assert [m.id for m in MIGRATIONS] == sorted(m.id for m in MIGRATIONS)
    assert MIGRATION in MIGRATIONS


def _mig(id, kind, **kw):
    return Migration(id, kind, (), lambda c: True, lambda c: None, **kw)


def test_pending_and_blocking():
    normal = _mig("0001-n", "normal")
    gate = _mig("0002-g", "major", gates_template=True)
    after = _mig("0003-a", "major", requires=("0002-g",))
    reg = (normal, gate, after)

    fresh = State(None, [])
    assert pending_normal(fresh, reg) == [normal]
    assert blocking_majors(fresh, reg) == [gate]
    assert available_majors(fresh, reg) == [gate]

    done = State(None, ["0002-g"])
    assert pending_normal(done, reg) == [normal]
    assert blocking_majors(done, reg) == []
    assert available_majors(done, reg) == [after]
