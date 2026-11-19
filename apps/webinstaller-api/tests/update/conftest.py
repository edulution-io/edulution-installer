from pathlib import Path

import pytest

from update.installation import COMPOSE, ENV, State, save_state, with_header

PRE_JULY_ENV = (
    "A=1\n"
    "MONGODB_PASSWORD=pw\n"
    "MONGODB_SERVER_URL=mongodb://root:pw@edu-db:27017/\n"
    "B=2\n"
)


@pytest.fixture
def make_installation(tmp_path, template_dir):
    def build(body=None, header=None, state=None, env=PRE_JULY_ENV) -> Path:
        if body is None:
            body = (template_dir / "docker-compose.yml.template").read_text(encoding="utf-8")
        text = with_header(body, header) if header else body
        (tmp_path / COMPOSE).write_bytes(text.encode("utf-8"))
        (tmp_path / ENV).write_bytes(env.encode("utf-8"))
        if state is not None:
            save_state(tmp_path, state)
        return tmp_path

    return build


@pytest.fixture
def target_text(template_dir):
    return (template_dir / "docker-compose.yml.template").read_text(encoding="utf-8")


@pytest.fixture
def all_applied():
    from update.migrations import MIGRATIONS

    return State("2.2.0", [m.id for m in MIGRATIONS])
