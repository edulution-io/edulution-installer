import fcntl
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
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


class UpdateError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Outcome:
    report: Report
    applied: list[str]  # ids recorded in this run, in order
    template_installed: bool
    recreate: list[str] = field(default_factory=list)  # services of the migrations that changed something


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


def _guard_downgrade(report: Report) -> None:
    if report.downgrade:
        raise UpdateError(
            5,
            f"Die Installation ist neuer als die Zielversion ({report.target_version}); Downgrade abgelehnt.",
        )


def _guard_template(report: Report, discard: bool) -> None:
    if report.status in ("modified", "unknown") and not discard:
        raise UpdateError(20, f"{COMPOSE} enthält lokale Änderungen; --discard-local-changes fehlt.")


def _guard_expect(root: Path, expect: str) -> None:
    if expect != fingerprint(root):
        raise UpdateError(4, "Die Dateien haben sich seit der Prüfung geändert.")


def _run_migration(migration, ctx: Context, state: State, ran: list) -> None:
    if migration.needed(ctx):
        migration.apply(ctx)
        ran.append(migration)
    state.applied.append(migration.id)


def _services(migrations) -> list[str]:
    return list(dict.fromkeys(name for m in migrations for name in m.recreate))


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
    os.chmod(root / ENV, 0o600)
    if compose_text is not None:
        atomic_write(root / COMPOSE, compose_text)
    save_state(root, state)


def _install_template(root, env, state, target_text, target_version, registry, ran) -> str:
    ctx = Context(root, env)
    for migration in pending_normal(state, registry):
        _run_migration(migration, ctx, state, ran)
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
) -> Outcome:
    with locked(root):
        report = check(root, target_text, target_version, history, registry)
        _guard_downgrade(report)
        if report.blocked_by:
            ids = ", ".join(m.id for m in report.blocked_by)
            raise UpdateError(30, f"Zuerst muss eine größere Migration ausgeführt werden: {ids}.")
        _guard_expect(root, expect)
        _guard_template(report, discard_local_changes)
        if exit_code(report) == 0:
            return Outcome(report, [], False)

        env = _read_env(root)
        original_env = env.render()
        state = load_state(root)
        recorded = len(state.applied)
        ran = []
        compose = _install_template(root, env, state, target_text, target_version, registry, ran)
        _commit(root, env, original_env, compose, state, now)
        report = check(root, target_text, target_version, history, registry)
        return Outcome(report, state.applied[recorded:], True, _services(ran))


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
) -> Outcome:
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
        report = check(root, target_text, target_version, history, registry)
        _guard_downgrade(report)
        # The last pending gating major installs the template; earlier ones only run their data step.
        installs_template = migration.gates_template and not any(
            m.kind == "major" and m.gates_template and m.id not in state.applied and m.id != migration_id
            for m in registry
        )
        if installs_template:
            _guard_template(report, discard_local_changes)

        env = _read_env(root)
        original_env = env.render()
        recorded = len(state.applied)
        ran = []
        _run_migration(migration, Context(root, env), state, ran)
        compose = None
        if installs_template:
            compose = _install_template(root, env, state, target_text, target_version, registry, ran)
        _commit(root, env, original_env, compose, state, now)
        report = check(root, target_text, target_version, history, registry)
        return Outcome(report, state.applied[recorded:], installs_template, _services(ran))


def init(root: Path, *, target_version: str, registry=MIGRATIONS) -> None:
    with locked(root):
        text = (root / COMPOSE).read_bytes().decode("utf-8")
        if read_header(text) is None:
            atomic_write(root / COMPOSE, with_header(text, target_version))
        save_state(root, State(target_version, [m.id for m in registry]))
