from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_provider, get_service, get_sync_service, settings_dep
from app.config import Settings
from app.db.session import get_db
from app.providers.base import ATSProvider
from app.services.recruiting import RecruitingService
from app.sync.service import SyncService

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    settings: Settings = Depends(settings_dep),
    provider: ATSProvider = Depends(get_provider),
    session: Session = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service),
) -> dict[str, Any]:
    db_ok = True
    db_message = "ok"
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db_ok = False
        db_message = "database_unavailable"

    provider_health = provider.health_check()
    status = "ok" if db_ok and provider_health.ok else "degraded"
    last_ok = sync_service.latest_successful_at()
    last_full = sync_service.latest_successful_at("full")
    last_incremental = sync_service.latest_successful_at("incremental")
    latest = sync_service.latest_run()
    return {
        "status": status,
        "provider": provider_health.provider,
        "provider_ok": provider_health.ok,
        "provider_message": provider_health.message,
        "capabilities": provider_health.capabilities,
        "database": db_message,
        "dry_run": settings.dry_run,
        "ai_enabled": settings.ai_enabled,
        "ai_provider": None,
        "configured": settings.provider_configured,
        "connection_state": (
            "not_configured"
            if not settings.provider_configured
            else "connected" if provider_health.ok else "disconnected"
        ),
        "connection": {
            "id": sync_service.connection.id,
            "provider": sync_service.connection.provider,
            "external_account_id": sync_service.connection.external_account_id,
            "account_name": sync_service.connection.account_name,
        },
        "last_successful_sync_at": last_ok.isoformat() if last_ok else None,
        "last_full_sync_at": last_full.isoformat() if last_full else None,
        "last_incremental_sync_at": last_incremental.isoformat() if last_incremental else None,
        "last_attempted_sync_at": latest.started_at.isoformat() if latest else None,
        "last_sync_status": latest.status.value if latest else None,
        "mirror": sync_service.mirror_counts(),
    }


@router.get("/provider/status")
def provider_status(
    settings: Settings = Depends(settings_dep),
    service: RecruitingService = Depends(get_service),
) -> dict[str, Any]:
    health = service.provider_health()
    return {
        "provider": health.provider,
        "ok": health.ok,
        "message": health.message,
        "capabilities": health.capabilities,
        "dry_run": settings.dry_run,
        "configured": settings.provider_configured,
        "ai_provider": None,
        "llm_api_required": False,
        "account_id": health.account_id,
        "account_name": health.account_name,
    }
