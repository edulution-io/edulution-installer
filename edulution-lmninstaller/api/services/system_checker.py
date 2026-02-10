import platform
from pathlib import Path

import yaml

from api.config import settings
from api.models import (
    CheckStatus,
    DiskInfo,
    RequirementCheck,
    RequirementsResponse,
    SystemInfo,
)


class SystemChecker:
    def _get_os_info(self) -> tuple[str | None, str | None]:
        try:
            info = platform.freedesktop_os_release()
            return info.get("NAME"), info.get("VERSION_ID")
        except OSError:
            return None, None

    def _get_ram_gb(self) -> float | None:
        try:
            meminfo = Path("/proc/meminfo").read_text()
            for line in meminfo.splitlines():
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return round(kb / 1024 / 1024, 1)
        except (OSError, ValueError, IndexError):
            pass
        return None

    def _get_disks(self) -> list[DiskInfo]:
        disks: list[DiskInfo] = []
        block_dir = Path("/sys/block")
        skip_prefixes = ("loop", "ram", "zram", "dm-", "sr", "fd")

        if not block_dir.exists():
            return disks

        for device in sorted(block_dir.iterdir()):
            if device.name.startswith(skip_prefixes):
                continue
            size_file = device / "size"
            if not size_file.exists():
                continue
            try:
                sectors = int(size_file.read_text().strip())
                size_gb = round(sectors * 512 / (1024**3), 1)
                if size_gb > 0:
                    disks.append(DiskInfo(name=device.name, size_gb=size_gb))
            except (OSError, ValueError):
                continue

        return disks

    def get_system_info(self) -> SystemInfo:
        os_name, os_version = self._get_os_info()
        return SystemInfo(
            os=os_name,
            os_version=os_version,
            ram_gb=self._get_ram_gb(),
            disks=self._get_disks(),
        )

    def _load_requirements(self, playbook: str) -> dict | None:
        req_file = settings.playbook_dir / "requirements" / playbook
        if not req_file.exists():
            return None
        return yaml.safe_load(req_file.read_text())

    def _check_os(
        self, reqs: dict, system: SystemInfo
    ) -> list[RequirementCheck]:
        checks: list[RequirementCheck] = []
        os_reqs = reqs.get("os")
        if not os_reqs:
            return checks

        req_distro = os_reqs.get("distribution")
        if req_distro:
            actual = system.os or "unknown"
            if actual.lower() == req_distro.lower():
                checks.append(
                    RequirementCheck(
                        name="os_distribution",
                        status=CheckStatus.PASSED,
                        required=req_distro,
                        actual=actual,
                        message=f"OS distribution is {actual}",
                    )
                )
            else:
                checks.append(
                    RequirementCheck(
                        name="os_distribution",
                        status=CheckStatus.FAILED,
                        required=req_distro,
                        actual=actual,
                        message=f"Expected {req_distro}, found {actual}",
                    )
                )

        req_version = os_reqs.get("min_version")
        if req_version:
            actual = system.os_version or "unknown"
            req_parts = [int(x) for x in str(req_version).split(".")]
            try:
                actual_parts = [int(x) for x in actual.split(".")]
                passed = actual_parts >= req_parts
            except ValueError:
                passed = False
            checks.append(
                RequirementCheck(
                    name="os_version",
                    status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
                    required=f">= {req_version}",
                    actual=actual,
                    message=f"OS version {actual} {'meets' if passed else 'does not meet'} minimum {req_version}",
                )
            )

        return checks

    def _check_ram(
        self, reqs: dict, system: SystemInfo
    ) -> list[RequirementCheck]:
        checks: list[RequirementCheck] = []
        ram_reqs = reqs.get("ram")
        if not ram_reqs:
            return checks

        min_gb = ram_reqs.get("min_gb")
        if min_gb is not None:
            actual = system.ram_gb
            if actual is None:
                checks.append(
                    RequirementCheck(
                        name="ram",
                        status=CheckStatus.FAILED,
                        required=f">= {min_gb} GB",
                        actual="unknown",
                        message="Could not determine RAM size",
                    )
                )
            else:
                passed = actual >= min_gb
                checks.append(
                    RequirementCheck(
                        name="ram",
                        status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
                        required=f">= {min_gb} GB",
                        actual=f"{actual} GB",
                        message=f"RAM {actual} GB {'meets' if passed else 'does not meet'} minimum {min_gb} GB",
                    )
                )

        return checks

    def _check_disks(
        self, reqs: dict, system: SystemInfo
    ) -> list[RequirementCheck]:
        checks: list[RequirementCheck] = []
        disk_reqs = reqs.get("disks")
        if not disk_reqs:
            return checks

        min_count = disk_reqs.get("min_count")
        if min_count is not None:
            actual_count = len(system.disks)
            passed = actual_count >= min_count
            checks.append(
                RequirementCheck(
                    name="disk_count",
                    status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
                    required=f">= {min_count}",
                    actual=str(actual_count),
                    message=f"Found {actual_count} disk(s), minimum is {min_count}",
                )
            )

        min_size_gb = disk_reqs.get("min_size_gb")
        if min_size_gb is not None:
            for disk in system.disks:
                passed = disk.size_gb >= min_size_gb
                checks.append(
                    RequirementCheck(
                        name=f"disk_size_{disk.name}",
                        status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
                        required=f">= {min_size_gb} GB",
                        actual=f"{disk.size_gb} GB",
                        message=f"Disk {disk.name} is {disk.size_gb} GB, minimum is {min_size_gb} GB",
                    )
                )

        return checks

    def check_requirements(self, playbook: str) -> RequirementsResponse:
        system = self.get_system_info()
        reqs = self._load_requirements(playbook)

        if reqs is None:
            return RequirementsResponse(
                playbook=playbook,
                all_passed=True,
                checks=[
                    RequirementCheck(
                        name="requirements_file",
                        status=CheckStatus.SKIPPED,
                        message=f"No requirements file found for {playbook}",
                    )
                ],
                system_info=system,
            )

        checks: list[RequirementCheck] = []
        checks.extend(self._check_os(reqs, system))
        checks.extend(self._check_ram(reqs, system))
        checks.extend(self._check_disks(reqs, system))

        all_passed = all(c.status != CheckStatus.FAILED for c in checks)

        return RequirementsResponse(
            playbook=playbook,
            all_passed=all_passed,
            checks=checks,
            system_info=system,
        )


system_checker = SystemChecker()
