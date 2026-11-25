import difflib
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from update.envfile import EnvFile
from update.installation import COMPOSE, ENV, load_state, read_header, strip_header
from update.migrations import (
    MIGRATIONS,
    Context,
    Migration,
    available_majors,
    blocking_majors,
    pending_normal,
)
from update.templates import sha256
from update.versions import is_older


@dataclass
class Report:
    status: Literal["current", "outdated", "modified", "unknown"]
    installed_version: str | None
    target_version: str
    header_current: bool
    downgrade: bool  # the target is older than the header or the state version
    pending: list[Migration]
    blocked_by: list[Migration]
    available_majors: list[Migration]
    recreate: list[str]
    expect: str
    diff: str
    restart_pending: bool = False  # update.sh restarted no services after its last apply
    db_credentials_missing: bool = False  # the update would start the database with access control


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return "-"


def fingerprint(root: Path) -> str:
    return f"{_file_hash(root / COMPOSE)}:{_file_hash(root / ENV)}"


def _needed(root: Path, pending: list[Migration]) -> list[Migration]:
    try:
        env = EnvFile.parse((root / ENV).read_bytes().decode("utf-8"))
    except FileNotFoundError:
        return pending  # apply refuses without the env file; until then nothing is known
    ctx = Context(root, env)
    return [m for m in pending if m.needed(ctx)]


# edu-api logs in with these two and ignores credentials in MONGODB_SERVER_URL.
DB_USER_KEYS = ("MONGODB_USERNAME", "MONGODB_PASSWORD")

DB_CREDENTIALS_MESSAGE = (
    f"edu-api erhält {' und '.join(DB_USER_KEYS)} nicht beide mit Wert. Nach dem Update startet die Datenbank "
    "mit Zugriffskontrolle (Replica Set mit Schlüsseldatei), und edu-api meldet sich mit diesen Werten an. "
    f"Zuerst einen Datenbank-Benutzer anlegen und in {ENV} (oder docker-compose.override.yml) eintragen."
)


def _db_user_missing(root: Path, service_env: dict[str, str] | None) -> bool:
    # What Compose passes to edu-api (overrides, interpolation) where update.sh could resolve it.
    if service_env is not None:
        return not all(service_env.get(key) for key in DB_USER_KEYS)
    try:
        env = EnvFile.parse((root / ENV).read_bytes().decode("utf-8"))
    except FileNotFoundError:
        return False
    return not all(env.get(key) for key in DB_USER_KEYS)


def db_credentials_missing(root: Path, compose_text: str, service_env: dict[str, str] | None) -> bool:
    """True if the compose file starts the database with access control and edu-api lacks its user."""
    return "--keyFile" in compose_text and _db_user_missing(root, service_env)


def check(
    root: Path,
    target_text: str,
    target_version: str,
    history: frozenset[str],
    registry=MIGRATIONS,
    restart_pending: bool = False,
    service_env: dict[str, str] | None = None,
) -> Report:
    # Bytes, not text mode: line-ending differences must count as differences.
    text = (root / COMPOSE).read_bytes().decode("utf-8")
    header = read_header(text)
    body = strip_header(text)
    state = load_state(root)

    if body == target_text:
        status = "current"
    elif sha256(body) in history:
        status = "outdated"
    else:
        status = "modified" if header is not None else "unknown"

    pending = pending_normal(state, registry)
    blocked_by = blocking_majors(state, registry)
    # Installations set up by hand may run the database without users; a template with a key file
    # turns on access control, which edu-api then cannot pass. Checked against what the next restart
    # starts, before anything is written: any change, even of the header alone, is followed by one.
    if blocked_by:
        # Only a major migration installs the target; until then a restart starts the installed files.
        db_missing = restart_pending and db_credentials_missing(root, text, service_env)
    else:
        changes = status != "current" or header != target_version or bool(pending) or restart_pending
        db_missing = changes and db_credentials_missing(root, target_text, service_env)
    recreate = list(dict.fromkeys(name for m in _needed(root, pending) for name in m.recreate))
    diff = "" if body == target_text else "".join(
        difflib.unified_diff(
            body.splitlines(keepends=True),
            target_text.splitlines(keepends=True),
            fromfile=COMPOSE,
            tofile=f"{COMPOSE} ({target_version})",
        )
    )
    return Report(
        status=status,
        installed_version=header if header is not None else state.template_version,
        target_version=target_version,
        header_current=header == target_version,
        downgrade=is_older(target_version, header) or is_older(target_version, state.template_version),
        pending=pending,
        blocked_by=blocked_by,
        available_majors=available_majors(state, registry),
        recreate=recreate,
        expect=fingerprint(root),
        diff=diff,
        restart_pending=restart_pending,
        db_credentials_missing=db_missing,
    )


def exit_code(report: Report) -> int:
    if report.downgrade:
        return 5
    if report.db_credentials_missing:
        return 6
    if report.blocked_by:
        return 30
    if report.status in ("modified", "unknown"):
        return 20
    if report.status == "outdated" or report.pending or not report.header_current or report.restart_pending:
        return 10
    return 0


def to_json(report: Report) -> dict:
    return {
        "exitCode": exit_code(report),
        "status": report.status,
        "installedVersion": report.installed_version,
        "targetVersion": report.target_version,
        "headerCurrent": report.header_current,
        "downgrade": report.downgrade,
        "restartPending": report.restart_pending,
        "dbCredentialsMissing": report.db_credentials_missing,
        "pendingMigrations": [
            {"id": m.id, "kind": m.kind, "recreate": list(m.recreate)} for m in report.pending
        ],
        "blockedBy": [m.id for m in report.blocked_by],
        "availableMajorMigrations": [m.id for m in report.available_majors],
        "recreate": report.recreate,
        "expect": report.expect,
        "diff": report.diff,
    }
