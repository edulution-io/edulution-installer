from fastapi import APIRouter, HTTPException

from api.models import (
    JobStatus,
    PlaybookStartRequest,
    PlaybookStartResponse,
    StatusResponse,
)
from api.services.ansible_runner import runner_service

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


@router.post("/playbook/start", response_model=PlaybookStartResponse)
async def start_playbook(request: PlaybookStartRequest) -> PlaybookStartResponse:
    if runner_service.status == JobStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="A playbook is already running",
        )

    try:
        job_id = await runner_service.run_playbook(
            playbook=request.playbook,
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
