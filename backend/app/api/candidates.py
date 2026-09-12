from fastapi import APIRouter, Depends, Query

from app.api.deps import get_service
from app.models.domain import Candidate, CandidateDetail
from app.services.recruiting import RecruitingService

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=list[Candidate])
def list_candidates(
    job_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: RecruitingService = Depends(get_service),
) -> list[Candidate]:
    return service.list_candidates(job_id, limit=limit, offset=offset)


@router.get("/{candidate_id}", response_model=CandidateDetail)
def get_candidate(
    candidate_id: str, service: RecruitingService = Depends(get_service)
) -> CandidateDetail:
    return service.get_candidate(candidate_id)
