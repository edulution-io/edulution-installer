import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

import ansible_runner

from api.config import settings
from api.models import JobStatus, MessageType
from api.services.output_streamer import streamer


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
        status_value = status.get("status", "")

        if status_value == "running":
            self._status = JobStatus.RUNNING
            streamer.queue_message(MessageType.STATUS, "running")
        elif status_value == "successful":
            self._status = JobStatus.COMPLETED
            self._finished_at = datetime.utcnow()
            self._return_code = 0
            streamer.queue_message(MessageType.STATUS, "completed")
            if self._shutdown_callback:
                self._shutdown_callback()
        elif status_value == "failed":
            self._status = JobStatus.FAILED
            self._finished_at = datetime.utcnow()
            self._return_code = 1
            streamer.queue_message(MessageType.STATUS, "failed")

        return True

    async def run_playbook(
        self, playbook: str, extra_vars: dict[str, Any]
    ) -> UUID:
        if self._status == JobStatus.RUNNING:
            raise RuntimeError("A playbook is already running")

        self._job_id = uuid4()
        self._status = JobStatus.RUNNING
        self._started_at = datetime.utcnow()
        self._finished_at = None
        self._return_code = None

        streamer.set_job_id(self._job_id)

        playbook_path = settings.playbook_dir / playbook
        private_data_dir = settings.private_data_dir

        private_data_dir.mkdir(parents=True, exist_ok=True)
        (private_data_dir / "project").mkdir(parents=True, exist_ok=True)
        (private_data_dir / "inventory").mkdir(parents=True, exist_ok=True)

        inventory_path = private_data_dir / "inventory" / "hosts"
        inventory_path.write_text("localhost ansible_connection=local\n")

        project_playbook = private_data_dir / "project" / playbook
        if playbook_path.exists():
            project_playbook.write_text(playbook_path.read_text())
        else:
            raise FileNotFoundError(f"Playbook not found: {playbook_path}")

        loop = asyncio.get_event_loop()

        def run_ansible():
            ansible_runner.run(
                private_data_dir=str(private_data_dir),
                playbook=playbook,
                extravars=extra_vars,
                event_handler=self._event_handler,
                status_handler=self._status_handler,
                quiet=True,
            )

        loop.run_in_executor(None, run_ansible)

        return self._job_id


runner_service = AnsibleRunnerService()
