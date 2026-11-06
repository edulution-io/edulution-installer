from pathlib import Path

import pytest

REPO_TEMPLATES = Path(__file__).resolve().parents[3] / "apps" / "public-page" / "public" / "download"


@pytest.fixture(autouse=True)
def template_dir(monkeypatch):
    monkeypatch.setenv("EDULUTION_TEMPLATE_DIR", str(REPO_TEMPLATES))
    return REPO_TEMPLATES
