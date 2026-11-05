#!/usr/bin/env python3
"""Regenerate app/update/template_history.json (run on a host with git).

Usage: python3 apps/webinstaller-api/tools/template_history.py [--check]
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = "apps/public-page/public/download/docker-compose.yml.template"
OUTPUT = Path(__file__).resolve().parents[1] / "app" / "update" / "template_history.json"
COMMAND = "python3 apps/webinstaller-api/tools/template_history.py"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True)


def digests() -> list[str]:
    log = git("log", "--format=%H", "--", TEMPLATE)
    if log.returncode != 0:
        sys.exit(f"git log failed: {log.stderr.decode().strip()}")
    found = set()
    for commit in log.stdout.decode().split():
        shown = git("show", f"{commit}:{TEMPLATE}")
        if shown.returncode == 0:
            found.add(hashlib.sha256(shown.stdout).hexdigest())
    found.add(hashlib.sha256((REPO / TEMPLATE).read_bytes()).hexdigest())
    return sorted(found)


def render() -> str:
    return json.dumps({"sha256": digests()}, indent=2) + "\n"


def main() -> int:
    content = render()
    if "--check" in sys.argv[1:]:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            print(f"template_history.json is out of date; regenerate it with: {COMMAND}", file=sys.stderr)
            return 1
        return 0
    OUTPUT.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
