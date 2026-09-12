from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm import AtsConnectionRecord
from app.providers.base import ATSProvider


def provider_account_id(provider: ATSProvider) -> str:
    value = getattr(provider, "account_id", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "default"


def provider_account_name(provider: ATSProvider) -> str | None:
    value = getattr(provider, "account_name", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def get_or_create_connection(session: Session, provider: ATSProvider) -> AtsConnectionRecord:
    """Resolve the ATS connection for this provider/account. Secrets stay in env, not here."""
    account_id = provider_account_id(provider)
    account_name = provider_account_name(provider)
    record = session.scalar(
        select(AtsConnectionRecord).where(
            AtsConnectionRecord.provider == provider.name,
            AtsConnectionRecord.external_account_id == account_id,
        )
    )
    now = datetime.now(UTC)
    if record is None:
        record = AtsConnectionRecord(
            id=str(uuid4()),
            provider=provider.name,
            external_account_id=account_id,
            account_name=account_name or account_id,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()
        return record
    if account_name and record.account_name != account_name:
        record.account_name = account_name
        record.updated_at = now
        session.flush()
    return record
