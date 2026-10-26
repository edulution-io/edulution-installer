from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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


# Extra vars override everything in the playbook, so only the settings an admin chooses get through:
# no download sources, proxies, package lists or Ansible connection variables.
ALLOWED_EXTRA_VARS = frozenset({
    "lmn_server_ip", "lmn_netmask", "lmn_gateway", "lmn_dns_forwarder",
    "lmn_servername", "lmn_domainname", "lmn_schoolname", "lmn_location", "lmn_country", "lmn_state",
    "lmn_dhcprange", "lmn_adminpw", "lmn_timezone", "lmn_locale",
    "lmn_skip_firewall", "lmn_unattended", "lmn_disable_auto_updates",
    "lmn_local_install", "lmn_webui_port",
    "lmn_setup_data_disk", "lmn_data_disk", "lmn_lvm_volumes",
})


class PlaybookVariables(BaseModel):
    extra_vars: dict[str, str | bool | int | float] = Field(default_factory=dict)

    @field_validator("extra_vars")
    @classmethod
    def only_allowed_names(cls, extra_vars: dict) -> dict:
        unknown = sorted(set(extra_vars) - ALLOWED_EXTRA_VARS)
        if unknown:
            raise ValueError(f"Not allowed: {', '.join(unknown)}")
        return extra_vars


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
