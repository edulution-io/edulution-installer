from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from update.envfile import EnvFile
from update.installation import State


@dataclass
class Context:
    root: Path
    env: EnvFile


@dataclass(frozen=True)
class Migration:
    id: str
    kind: Literal["normal", "major"]
    recreate: tuple[str, ...]
    needed: Callable[[Context], bool]
    apply: Callable[[Context], None]  # may only mutate ctx.env; the runner backs up and writes files
    requires: tuple[str, ...] = ()
    gates_template: bool = False


def pending_normal(state: State, registry=None) -> list[Migration]:
    registry = MIGRATIONS if registry is None else registry
    return [m for m in registry if m.kind == "normal" and m.id not in state.applied]


def blocking_majors(state: State, registry=None) -> list[Migration]:
    registry = MIGRATIONS if registry is None else registry
    return [
        m for m in registry
        if m.kind == "major" and m.gates_template and m.id not in state.applied
    ]


def available_majors(state: State, registry=None) -> list[Migration]:
    registry = MIGRATIONS if registry is None else registry
    return [
        m for m in registry
        if m.kind == "major"
        and m.id not in state.applied
        and all(r in state.applied for r in m.requires)
    ]


# Imported last: the migration modules import Context and Migration from here.
from update.migrations import m0001_mongo_replica_set  # noqa: E402

MIGRATIONS: tuple[Migration, ...] = tuple(
    sorted((m0001_mongo_replica_set.MIGRATION,), key=lambda m: m.id)
)
