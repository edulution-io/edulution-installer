import asyncio
import os
import shutil
import signal
import time

from api.config import settings
from api.models import JobStatus

_last_activity = time.monotonic()


def touch() -> None:
    global _last_activity
    _last_activity = time.monotonic()


def should_stop(runner) -> bool:
    # A run counts as activity, so the full time is left after it ends to fetch the result.
    if runner.status == JobStatus.RUNNING:
        touch()
        return False
    return time.monotonic() - _last_activity >= settings.idle_shutdown


async def stop_when_idle(runner) -> None:
    """Stops the API once nobody has used it for settings.idle_shutdown seconds outside a playbook run,
    e.g. after a failed run or when the wizard was left; 0 keeps it running."""
    if settings.idle_shutdown <= 0:
        return
    while True:
        await asyncio.sleep(min(60, settings.idle_shutdown))
        if should_stop(runner):
            os.kill(os.getpid(), signal.SIGTERM)
            return


def remove_install_leftovers() -> None:
    """Run logs, run parameters and the binduser handover are only needed during the install;
    the next playbook run creates them again."""
    for directory in ("artifacts", "env"):
        shutil.rmtree(settings.private_data_dir / directory, ignore_errors=True)
    settings.edulution_config_path.unlink(missing_ok=True)
