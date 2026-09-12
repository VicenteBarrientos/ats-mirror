from __future__ import annotations

import threading
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_provider, get_sync_service, settings_dep
from app.config import Settings
from app.db.session import get_db
from app.models.domain import SyncRun
from app.models.mappers import sync_run_from_record
from app.models.orm import AtsConnectionRecord, SyncRunRecord
from app.providers.base import ATSProvider
from app.providers.errors import EntityNotFoundError
from app.sync.service import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])

_SYNC_LOCK = threading.Lock()


@router.post("", response_model=SyncRun)
def sync_all(
    request: Request,
    service: SyncService = Depends(get_sync_service),
) -> SyncRun:
    return _run_exclusive(request, service.sync_all)


@router.post("/incremental", response_model=SyncRun)
def sync_incremental(
    request: Request,
    service: SyncService = Depends(get_sync_service),
) -> SyncRun:
    return _run_exclusive(request, service.sync_incremental)


@router.post("/jobs", response_model=SyncRun)
def sync_jobs(
    request: Request,
    service: SyncService = Depends(get_sync_service),
) -> SyncRun:
    return _run_exclusive(request, service.sync_jobs)


@router.post("/candidates", response_model=SyncRun)
def sync_candidates(
    request: Request,
    service: SyncService = Depends(get_sync_service),
) -> SyncRun:
    return _run_exclusive(request, service.sync_candidates)


@router.get("/status")
def sync_status(
    service: SyncService = Depends(get_sync_service),
    provider: ATSProvider = Depends(get_provider),
    settings: Settings = Depends(settings_dep),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    health = provider.health_check()
    latest = service.latest_run()
    last_ok = service.latest_successful_at()
    last_full = service.latest_successful_at("full")
    last_incremental = service.latest_successful_at("incremental")
    last_attempted = latest.started_at.isoformat() if latest else None
    return {
        "provider": provider.name,
        "configured": settings.provider_configured,
        "connection_ok": health.ok,
        "connection_message": health.message,
        "connection_state": _connection_state(
            configured=settings.provider_configured,
            ok=health.ok,
            last_run=latest,
        ),
        "connection": {
            "id": service.connection.id,
            "provider": service.connection.provider,
            "external_account_id": service.connection.external_account_id,
            "account_name": service.connection.account_name,
        },
        "connections": [
            {
                "id": row.id,
                "provider": row.provider,
                "external_account_id": row.external_account_id,
                "account_name": row.account_name,
            }
            for row in session.scalars(
                select(AtsConnectionRecord).order_by(AtsConnectionRecord.account_name)
            ).all()
        ],
        "last_successful_sync_at": last_ok.isoformat() if last_ok else None,
        "last_full_sync_at": last_full.isoformat() if last_full else None,
        "last_incremental_sync_at": last_incremental.isoformat() if last_incremental else None,
        "last_attempted_sync_at": last_attempted,
        "current_sync_status": latest.status.value if latest else None,
        "watermarks": service.watermark_status(),
        "last_run": latest.model_dump(mode="json") if latest else None,
        "counts": service.mirror_counts(),
        "metric_notes": {
            "jobs_seen": "Jobs fetched from the ATS during this run",
            "candidates_seen": "Candidates fetched from the ATS during this run",
            "applications_seen": "Applications fetched during this run",
            "events_seen": "Events/activities fetched during this run",
            "stages_seen": "Stages fetched during this run",
            "files_seen": "File-metadata records fetched during this run",
            "source_objects_fetched": "Sum of the per-type fetched counts above",
            "created_count": "Canonical rows created (jobs, candidates, applications, stages, events, files)",
            "updated_count": "Canonical rows whose source-controlled content changed",
            "unchanged_count": "Canonical rows observed with unchanged content_hash",
            "raw_objects_*": "Separate counters for raw_ats_objects upserts",
        },
        "ai_provider": None,
        "llm_api_required": False,
    }


@router.get("/runs", response_model=list[SyncRun])
def list_sync_runs(
    service: SyncService = Depends(get_sync_service),
) -> list[SyncRun]:
    return service.list_runs()


@router.get("/runs/{run_id}", response_model=SyncRun)
def get_sync_run(
    run_id: str,
    session: Session = Depends(get_db),
) -> SyncRun:
    record = session.scalar(
        select(SyncRunRecord)
        .options(selectinload(SyncRunRecord.errors), selectinload(SyncRunRecord.connection))
        .where(SyncRunRecord.id == run_id)
    )
    if record is None:
        raise EntityNotFoundError("sync_run", run_id)
    return sync_run_from_record(record, include_errors=True)


def _run_exclusive(_request: Request, action: Callable[[], SyncRun]) -> SyncRun:
    if not _SYNC_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A sync is already running.")
    try:
        return action()
    finally:
        _SYNC_LOCK.release()


def _connection_state(*, configured: bool, ok: bool, last_run: SyncRun | None) -> str:
    if not configured:
        return "not_configured"
    if last_run is not None and last_run.status.value == "running":
        return "syncing"
    if not ok:
        return "disconnected"
    if last_run is None:
        return "connected"
    if last_run.status.value == "failed":
        return "last_sync_failed"
    if last_run.status.value in {"completed", "completed_with_errors"}:
        return "last_sync_succeeded"
    return "connected"
