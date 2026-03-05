import json
import os
import signal
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.models import (
    JobStatus,
    PlaybookStartRequest,
    PlaybookStartResponse,
    RequirementsResponse,
    StatusResponse,
)
from api.services.ansible_runner import runner_service
from api.services.system_checker import system_checker

EDULUTION_CONFIG_PATH = Path("/var/lib/edulution/binduser-config.json")

router = APIRouter(prefix="/api", tags=["playbook"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    return StatusResponse(
        status=runner_service.status,
        job_id=runner_service.job_id,
        started_at=runner_service.started_at,
        finished_at=runner_service.finished_at,
        return_code=runner_service.return_code,
    )


@router.post("/playbook/{playbook}/start", response_model=PlaybookStartResponse)
async def start_playbook(
    playbook: str, request: PlaybookStartRequest
) -> PlaybookStartResponse:
    if runner_service.status == JobStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="A playbook is already running",
        )

    try:
        job_id = await runner_service.run_playbook(
            playbook=playbook,
            extra_vars=request.variables.extra_vars,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PlaybookStartResponse(
        job_id=job_id,
        status=JobStatus.RUNNING,
        message="Playbook started successfully",
    )


@router.get(
    "/playbook/{playbook}/requirements", response_model=RequirementsResponse
)
async def check_requirements(playbook: str) -> RequirementsResponse:
    return system_checker.check_requirements(playbook)


@router.get("/network-info")
async def get_network_info() -> dict:
    import subprocess

    result: dict = {}
    try:
        out = subprocess.run(
            ["ip", "-j", "route", "show", "default"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            import json as _json
            routes = _json.loads(out.stdout)
            if routes:
                result["gateway"] = routes[0].get("gateway", "")
                iface = routes[0].get("dev", "")
                result["interface"] = iface

                addr_out = subprocess.run(
                    ["ip", "-j", "-4", "addr", "show", iface],
                    capture_output=True, text=True, timeout=5,
                )
                if addr_out.returncode == 0:
                    addrs = _json.loads(addr_out.stdout)
                    if addrs and addrs[0].get("addr_info"):
                        info = addrs[0]["addr_info"][0]
                        result["ip"] = info.get("local", "")
                        prefix = info.get("prefixlen", 24)
                        # CIDR prefix to subnet mask
                        mask_int = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
                        result["netmask"] = ".".join(
                            str((mask_int >> (8 * i)) & 0xFF) for i in range(3, -1, -1)
                        )
    except Exception:
        pass

    try:
        import socket
        result["hostname"] = socket.gethostname()
    except Exception:
        pass

    return result


@router.get("/edulution-config")
async def get_edulution_config() -> dict:
    if not EDULUTION_CONFIG_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Edulution config not found. Playbook may not have completed successfully.",
        )
    try:
        return json.loads(EDULUTION_CONFIG_PATH.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")


@router.post("/shutdown")
async def shutdown() -> dict[str, str]:
    def delayed_shutdown():
        import time
        time.sleep(2)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=delayed_shutdown, daemon=True).start()
    return {"status": "ok", "message": "Server wird heruntergefahren"}
