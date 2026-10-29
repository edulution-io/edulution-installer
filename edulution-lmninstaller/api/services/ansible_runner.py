import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

import ansible_runner

from api.config import settings
from api.models import JobStatus, MessageType
from api.services.output_streamer import streamer


def _unsafe(value: Any) -> Any:
    """Marks every string so Ansible takes it as entered instead of as a template."""
    if isinstance(value, str):
        return {"__ansible_unsafe": value}
    if isinstance(value, list):
        return [_unsafe(item) for item in value]
    if isinstance(value, dict):
        return {key: _unsafe(item) for key, item in value.items()}
    return value


class AnsibleRunnerService:
    def __init__(self):
        self._status: JobStatus = JobStatus.IDLE
        self._job_id: UUID | None = None
        self._started_at: datetime | None = None
        self._finished_at: datetime | None = None
        self._return_code: int | None = None
        self._thread = None
        self._shutdown_callback: Callable[[], None] | None = None

    @property
    def status(self) -> JobStatus:
        return self._status

    @property
    def job_id(self) -> UUID | None:
        return self._job_id

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def finished_at(self) -> datetime | None:
        return self._finished_at

    @property
    def return_code(self) -> int | None:
        return self._return_code

    def set_shutdown_callback(self, callback: Callable[[], None]) -> None:
        self._shutdown_callback = callback

    def _event_handler(self, event: dict[str, Any]) -> bool:
        event_type = event.get("event", "")

        if "stdout" in event:
            stdout = event["stdout"]
            if stdout:
                streamer.queue_message(MessageType.STDOUT, stdout)

        event_data = event.get("event_data", {})
        if event_type == "runner_on_failed":
            task = event_data.get("task", "unknown")
            streamer.queue_message(MessageType.EVENT, f"Task failed: {task}")
        elif event_type == "runner_on_ok":
            task = event_data.get("task", "unknown")
            streamer.queue_message(MessageType.EVENT, f"Task OK: {task}")
        elif event_type == "playbook_on_play_start":
            play = event_data.get("play", "unknown")
            streamer.queue_message(MessageType.EVENT, f"Play started: {play}")
        elif event_type == "playbook_on_stats":
            streamer.queue_message(MessageType.EVENT, "Playbook finished")

        return True

    def _status_handler(self, status: dict[str, Any], runner_config: Any) -> bool:
        # The end of a run is recorded in _finish, once its settings file is gone.
        if status.get("status") == "running":
            streamer.queue_message(MessageType.STATUS, "running")

        return True

    def _finish(self, successful: bool) -> None:
        # Streamed first: once the status changes, a new run may set its own job id.
        streamer.queue_message(MessageType.STATUS, "completed" if successful else "failed")
        self._finished_at = datetime.utcnow()
        self._return_code = 0 if successful else 1
        self._status = JobStatus.COMPLETED if successful else JobStatus.FAILED

    async def run_playbook(
        self, playbook: str, extra_vars: dict[str, Any]
    ) -> UUID:
        if self._status == JobStatus.RUNNING:
            raise RuntimeError("A playbook is already running")

        playbook_path = settings.playbook_dir / playbook
        if not playbook_path.is_file():
            raise FileNotFoundError(f"Playbook not found: {playbook_path}")

        private_data_dir = settings.private_data_dir

        private_data_dir.mkdir(parents=True, exist_ok=True)
        (private_data_dir / "project").mkdir(parents=True, exist_ok=True)
        (private_data_dir / "inventory").mkdir(parents=True, exist_ok=True)

        inventory_path = private_data_dir / "inventory" / "hosts"
        inventory_path.write_text("localhost ansible_connection=local\n")

        (private_data_dir / "project" / playbook).write_text(playbook_path.read_text())

        # Written here and removed after the run: given a dict, ansible-runner writes env/extravars only
        # if there is none yet (otherwise passes it inline) and never removes it.
        env_dir = private_data_dir / "env"
        env_dir.mkdir(mode=0o700, exist_ok=True)
        extravars_path = env_dir / "extravars"
        fd = os.open(extravars_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(_unsafe(extra_vars), f)

        # Counts as started only now, so a failure while preparing does not leave it running.
        self._job_id = uuid4()
        self._status = JobStatus.RUNNING
        self._started_at = datetime.utcnow()
        self._finished_at = None
        self._return_code = None
        streamer.set_job_id(self._job_id)

        loop = asyncio.get_event_loop()

        def run_ansible():
            successful = False
            try:
                successful = ansible_runner.run(
                    private_data_dir=str(private_data_dir),
                    playbook=playbook,
                    event_handler=self._event_handler,
                    status_handler=self._status_handler,
                    quiet=True,
                ).status == "successful"
            except Exception as e:
                streamer.queue_message(MessageType.STDERR, f"ansible-runner: {e}")
            finally:
                try:
                    extravars_path.unlink(missing_ok=True)
                finally:
                    self._finish(successful)

        loop.run_in_executor(None, run_ansible)

        return self._job_id


runner_service = AnsibleRunnerService()
