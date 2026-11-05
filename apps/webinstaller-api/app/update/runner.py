import fcntl
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from update.drift import Report, check, exit_code, fingerprint
from update.envfile import EnvFile
from update.installation import (
    COMPOSE,
    ENV,
    LOCK,
    STATE,
    State,
    atomic_write,
    backup,
    load_state,
    read_header,
    save_state,
    with_header,
)
from update.migrations import MIGRATIONS, Context, pending_normal
from update.versions import is_older


class UpdateError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@contextmanager
def locked(root: Path):
    fd = os.open(root / LOCK, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise UpdateError(3, "Ein anderes Update läuft bereits.") from None
        yield
    finally:
        os.close(fd)


def _read_env(root: Path) -> EnvFile:
    try:
        text = (root / ENV).read_bytes().decode("utf-8")
    except FileNotFoundError:
        raise UpdateError(1, f"{ENV} fehlt im Installationsverzeichnis.") from None
    return EnvFile.parse(text)


def _guard_template(report: Report, target_version: str, discard: bool) -> None:
    if report.installed_version is not None and is_older(target_version, report.installed_version):
        raise UpdateError(
            5,
            f"Die installierte Vorlage ({report.installed_version}) ist neuer als "
            f"die Zielversion ({target_version}); Downgrade abgelehnt.",
        )
    if report.status in ("modified", "unknown") and not discard:
        raise UpdateError(20, f"{COMPOSE} enthält lokale Änderungen; --discard-local-changes fehlt.")


def _guard_expect(root: Path, expect: str) -> None:
    if expect != fingerprint(root):
        raise UpdateError(4, "Die Dateien haben sich seit der Prüfung geändert.")


def _run_migration(migration, ctx: Context, state: State) -> None:
    if migration.needed(ctx):
        migration.apply(ctx)
    state.applied.append(migration.id)


def _commit(
    root: Path,
    env: EnvFile,
    original_env: str,
    compose_text: str | None,
    state: State,
    now: datetime | None,
) -> None:
    # Everything was computed in memory; from here on only the backup and the writes happen.
    backup(root, [COMPOSE, ENV, STATE], now)
    rendered = env.render()
    if rendered != original_env:
        atomic_write(root / ENV, rendered, mode=0o600)
    if compose_text is not None:
        atomic_write(root / COMPOSE, compose_text)
    save_state(root, state)


def _install_template(root, env, state, target_text, target_version, registry) -> str:
    ctx = Context(root, env)
    for migration in pending_normal(state, registry):
        _run_migration(migration, ctx, state)
    state.template_version = target_version
    return with_header(target_text, target_version)


def apply(
    root: Path,
    *,
    expect: str,
    discard_local_changes: bool,
    target_text: str,
    target_version: str,
    history: frozenset[str],
    registry=MIGRATIONS,
    now: datetime | None = None,
) -> Report:
    with locked(root):
        report = check(root, target_text, target_version, history, registry)
        if report.blocked_by:
            ids = ", ".join(m.id for m in report.blocked_by)
            raise UpdateError(30, f"Zuerst muss eine größere Migration ausgeführt werden: {ids}.")
        _guard_expect(root, expect)
        _guard_template(report, target_version, discard_local_changes)
        if exit_code(report) == 0:
            return report

        env = _read_env(root)
        original_env = env.render()
        state = load_state(root)
        compose = _install_template(root, env, state, target_text, target_version, registry)
        _commit(root, env, original_env, compose, state, now)
        return check(root, target_text, target_version, history, registry)


def migrate(
    root: Path,
    migration_id: str,
    *,
    expect: str,
    target_text: str,
    target_version: str,
    history: frozenset[str],
    registry=MIGRATIONS,
    now: datetime | None = None,
    discard_local_changes: bool = False,
) -> Report:
    with locked(root):
        migration = next((m for m in registry if m.id == migration_id), None)
        if migration is None or migration.kind != "major":
            raise UpdateError(2, f"Unbekannte Migration: {migration_id}.")
        state = load_state(root)
        if migration_id in state.applied:
            raise UpdateError(2, f"Migration {migration_id} wurde bereits ausgeführt.")
        missing = [r for r in migration.requires if r not in state.applied]
        if missing:
            raise UpdateError(2, f"Zuerst erforderlich: {', '.join(missing)}.")
        _guard_expect(root, expect)
        if migration.gates_template:
            report = check(root, target_text, target_version, history, registry)
            _guard_template(report, target_version, discard_local_changes)

        env = _read_env(root)
        original_env = env.render()
        _run_migration(migration, Context(root, env), state)
        compose = None
        if migration.gates_template:
            compose = _install_template(root, env, state, target_text, target_version, registry)
        _commit(root, env, original_env, compose, state, now)
        return check(root, target_text, target_version, history, registry)


def init(root: Path, *, target_version: str, registry=MIGRATIONS) -> None:
    with locked(root):
        text = (root / COMPOSE).read_bytes().decode("utf-8")
        if read_header(text) is None:
            atomic_write(root / COMPOSE, with_header(text, target_version))
        save_state(root, State(target_version, [m.id for m in registry]))
