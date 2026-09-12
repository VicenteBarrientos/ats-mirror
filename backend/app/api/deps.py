from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.providers.base import ATSProvider
from app.services.recruiting import RecruitingService
from app.sync.service import SyncService


def settings_dep() -> Settings:
    return get_settings()


def get_provider(request: Request) -> ATSProvider:
    provider = getattr(request.app.state, "provider", None)
    if provider is None:
        raise RuntimeError("ATS provider is not initialized.")
    return provider  # type: ignore[no-any-return]


def get_service(
    session: Session = Depends(get_db),
    provider: ATSProvider = Depends(get_provider),
) -> Generator[RecruitingService, None, None]:
    yield RecruitingService(session, provider)


def get_sync_service(
    session: Session = Depends(get_db),
    provider: ATSProvider = Depends(get_provider),
) -> Generator[SyncService, None, None]:
    yield SyncService(session, provider)
