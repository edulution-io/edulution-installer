import hashlib
import json
import os
from pathlib import Path

TEMPLATE_DIR = Path(os.environ.get("EDULUTION_TEMPLATE_DIR", "/app/templates"))


def target_version() -> str:
    return os.environ.get("INSTALLER_VERSION", "dev")


def target_compose() -> str:
    # Read the directory at call time so tests can point it elsewhere.
    directory = Path(os.environ.get("EDULUTION_TEMPLATE_DIR", str(TEMPLATE_DIR)))
    return (directory / "docker-compose.yml.template").read_text(encoding="utf-8")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def history() -> frozenset[str]:
    path = Path(__file__).with_name("template_history.json")
    return frozenset(json.loads(path.read_text(encoding="utf-8"))["sha256"])
