from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RequirementCheck(BaseModel):
    name: str
    status: CheckStatus
    required: str | None = None
    actual: str | None = None
    message: str


class DiskInfo(BaseModel):
    name: str
    size_gb: float


class SystemInfo(BaseModel):
    os: str | None = None
    os_version: str | None = None
    ram_gb: float | None = None
    disks: list[DiskInfo] = Field(default_factory=list)


class RequirementsResponse(BaseModel):
    playbook: str
    all_passed: bool
    checks: list[RequirementCheck] = Field(default_factory=list)
    system_info: SystemInfo


class PlaybookVariables(BaseModel):
    extra_vars: dict[str, Any] = Field(default_factory=dict)


class PlaybookStartRequest(BaseModel):
    variables: PlaybookVariables = Field(default_factory=PlaybookVariables)


class PlaybookStartResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    message: str


class StatusResponse(BaseModel):
    status: JobStatus
    job_id: UUID | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    return_code: int | None = None


class MessageType(str, Enum):
    STDOUT = "stdout"
    STDERR = "stderr"
    EVENT = "event"
    STATUS = "status"


class WebSocketMessage(BaseModel):
    type: MessageType
    data: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    job_id: UUID | None = None
