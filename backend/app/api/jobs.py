from fastapi import APIRouter, Depends, Query

from app.api.deps import get_service
from app.models.domain import Job
from app.services.recruiting import RecruitingService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[Job])
def list_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: RecruitingService = Depends(get_service),
) -> list[Job]:
    return service.list_jobs(limit=limit, offset=offset)


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str, service: RecruitingService = Depends(get_service)) -> Job:
    return service.get_job(job_id)
