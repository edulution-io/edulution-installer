import ipaddress
import re
import unicodedata
from datetime import datetime
from enum import Enum
from typing import Any, Callable
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


def _ipv4(value: Any) -> bool:
    try:
        ipaddress.IPv4Address(value)
        return isinstance(value, str)
    except ValueError:
        return False


def _matches(pattern: str) -> Callable[[Any], bool]:
    regex = re.compile(pattern)
    return lambda value: isinstance(value, str) and regex.fullmatch(value) is not None


def _ini_text(value: Any) -> bool:
    # setup.ini is read with ConfigParser, for which % and $ are not plain characters.
    return (
        isinstance(value, str)
        and not any(unicodedata.category(char) in ("Cc", "Zl", "Zp") for char in value)
        and not set(value) & {"%", "$"}
    )


def _flag(value: Any) -> bool:
    return isinstance(value, bool)


def _dhcprange(value: Any) -> bool:
    parts = value.split(" ") if isinstance(value, str) else []
    return len(parts) == 2 and all(map(_ipv4, parts))


def _data_disk(value: Any) -> bool:
    return _matches(r"(/dev/[A-Za-z0-9/_.:-]+)?")(value) and ".." not in value


# Extra vars override everything in the playbook, so only the settings an admin chooses get through,
# each in the form the playbook uses it in shell commands and setup.ini.
ALLOWED_EXTRA_VARS: dict[str, Callable[[Any], bool]] = {
    "lmn_server_ip": _ipv4,
    "lmn_netmask": _ipv4,
    "lmn_gateway": _ipv4,
    "lmn_dns_forwarder": lambda value: value == "auto" or _ipv4(value),
    "lmn_dhcprange": _dhcprange,
    "lmn_servername": _matches(r"[a-z][a-z0-9-]{0,14}"),
    "lmn_domainname": _matches(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+"),
    "lmn_schoolname": _ini_text,
    "lmn_location": _ini_text,
    "lmn_country": _matches(r"[a-z]{2}"),
    "lmn_state": _ini_text,
    # The characters the web installer allows for the admin password.
    "lmn_adminpw": _matches(r"[A-Za-z0-9!#@&*()\[\]{}+\-=_.,?§]+"),
    "lmn_timezone": _matches(r"[A-Za-z0-9_+-]+(/[A-Za-z0-9_+-]+)*"),
    "lmn_locale": _matches(r"[A-Za-z_]+(\.[A-Za-z0-9-]+)?(@[A-Za-z]+)?"),
    "lmn_skip_firewall": _flag,
    "lmn_unattended": _flag,
    "lmn_disable_auto_updates": _flag,
    "lmn_local_install": _flag,
    "lmn_webui_port": lambda value: type(value) is int and 1 <= value <= 65535,
    "lmn_setup_data_disk": _flag,
    "lmn_data_disk": _data_disk,
    "lmn_lvm_volumes": _matches(r"([a-z0-9-]+:\d+(%FREE)?(,[a-z0-9-]+:\d+(%FREE)?)*)?"),
}

# Names and codes linuxmuster expects in lower case, and a DHCP range as two addresses.
NORMALISE: dict[str, Callable[[str], str]] = {
    "lmn_servername": str.lower,
    "lmn_domainname": str.lower,
    "lmn_country": str.lower,
    "lmn_dhcprange": lambda value: " ".join(value.split()),
}


class PlaybookVariables(BaseModel):
    extra_vars: dict[str, str | bool | int] = Field(default_factory=dict)

    @field_validator("extra_vars")
    @classmethod
    def only_allowed_settings(cls, extra_vars: dict) -> dict:
        unknown = sorted(set(extra_vars) - set(ALLOWED_EXTRA_VARS))
        if unknown:
            raise ValueError(f"Not allowed: {', '.join(unknown)}")
        extra_vars = {
            name: NORMALISE[name](value) if name in NORMALISE and isinstance(value, str) else value
            for name, value in extra_vars.items()
        }
        invalid = sorted(name for name, value in extra_vars.items() if not ALLOWED_EXTRA_VARS[name](value))
        if invalid:
            raise ValueError(f"Invalid value: {', '.join(invalid)}")
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
