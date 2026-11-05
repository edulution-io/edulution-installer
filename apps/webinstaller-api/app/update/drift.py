import difflib
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from update.installation import COMPOSE, ENV, load_state, read_header, strip_header
from update.migrations import (
    MIGRATIONS,
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


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return "-"


def fingerprint(root: Path) -> str:
    return f"{_file_hash(root / COMPOSE)}:{_file_hash(root / ENV)}"


def check(
    root: Path,
    target_text: str,
    target_version: str,
    history: frozenset[str],
    registry=MIGRATIONS,
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
    recreate = list(dict.fromkeys(name for m in pending for name in m.recreate))
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
        blocked_by=blocking_majors(state, registry),
        available_majors=available_majors(state, registry),
        recreate=recreate,
        expect=fingerprint(root),
        diff=diff,
    )


def exit_code(report: Report) -> int:
    if report.downgrade:
        return 5
    if report.blocked_by:
        return 30
    if report.status in ("modified", "unknown"):
        return 20
    if report.status == "outdated" or report.pending or not report.header_current:
        return 10
    return 0


def to_json(report: Report) -> dict:
    return {
        "status": report.status,
        "installedVersion": report.installed_version,
        "targetVersion": report.target_version,
        "pendingMigrations": [
            {"id": m.id, "kind": m.kind, "recreate": list(m.recreate)} for m in report.pending
        ],
        "blockedBy": [m.id for m in report.blocked_by],
        "availableMajorMigrations": [m.id for m in report.available_majors],
        "recreate": report.recreate,
        "expect": report.expect,
        "diff": report.diff,
    }
