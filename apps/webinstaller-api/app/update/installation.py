import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

COMPOSE = "docker-compose.yml"
ENV = "edulution.env"
STATE = "edulution-update.json"
LOCK = "edulution-update.lock"
BACKUP_DIR = "docker-compose-backups"
HEADER_PREFIX = "# edulution-installer template "


def read_header(text: str) -> str | None:
    first = text.split("\n", 1)[0].rstrip("\r")
    if first.startswith(HEADER_PREFIX):
        return first[len(HEADER_PREFIX):].strip()
    return None


def strip_header(text: str) -> str:
    if read_header(text) is None:
        return text
    return text.split("\n", 1)[1] if "\n" in text else ""


def with_header(body: str, version: str) -> str:
    return f"{HEADER_PREFIX}{version}\n{body}"


@dataclass
class State:
    template_version: str | None = None
    applied: list[str] = field(default_factory=list)


def load_state(root: Path) -> State:
    path = root / STATE
    if not path.exists():
        return State(None, [])
    data = json.loads(path.read_text(encoding="utf-8"))
    return State(data.get("templateVersion"), list(data.get("applied", [])))


def save_state(root: Path, state: State) -> None:
    payload = {"templateVersion": state.template_version, "applied": state.applied}
    atomic_write(root / STATE, json.dumps(payload, indent=2) + "\n")


def atomic_write(path: Path, text: str, mode: int | None = None) -> None:
    if mode is None:
        mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def backup(root: Path, names: list[str], now: datetime | None = None) -> list[Path]:
    stamp = (now or datetime.now()).strftime("%Y-%m-%dT%H-%M-%S")
    directory = root / BACKUP_DIR
    directory.mkdir(parents=True, exist_ok=True)
    created = []
    for name in names:
        source = root / name
        if not source.exists():
            continue
        data = source.read_bytes()
        mode = 0o600 if name == ENV else 0o644
        suffix = 0
        while True:
            tag = stamp if suffix == 0 else f"{stamp}-{suffix}"
            target = directory / f"{name}.{tag}.backup"
            try:
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
            except FileExistsError:
                suffix += 1
                continue
            break
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(target, mode)
        created.append(target)
    return created
