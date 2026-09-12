from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm import SyncWatermarkRecord

SCOPE_JOBS = "jobs"
SCOPE_CANDIDATES = "candidates"
SCOPE_EVENTS = "events"
SCOPE_MIRROR = "mirror"

INCREMENTAL_SCOPES = (SCOPE_JOBS, SCOPE_CANDIDATES, SCOPE_EVENTS)


def get_watermark(session: Session, connection_id: str, scope: str) -> SyncWatermarkRecord | None:
    return session.scalar(
        select(SyncWatermarkRecord).where(
            SyncWatermarkRecord.connection_id == connection_id,
            SyncWatermarkRecord.sync_scope == scope,
        )
    )


def list_watermarks(session: Session, connection_id: str) -> dict[str, SyncWatermarkRecord]:
    rows = session.scalars(
        select(SyncWatermarkRecord).where(SyncWatermarkRecord.connection_id == connection_id)
    ).all()
    return {row.sync_scope: row for row in rows}


def mark_attempt(session: Session, connection_id: str, scope: str, when: datetime) -> SyncWatermarkRecord:
    record = get_watermark(session, connection_id, scope)
    if record is None:
        record = SyncWatermarkRecord(
            id=str(uuid4()),
            connection_id=connection_id,
            sync_scope=scope,
            last_successful_watermark=None,
            last_attempt_at=when,
            last_success_at=None,
        )
        session.add(record)
    else:
        record.last_attempt_at = when
    session.flush()
    return record


def advance_watermark(
    session: Session,
    connection_id: str,
    scope: str,
    watermark: datetime,
    *,
    succeeded_at: datetime | None = None,
) -> SyncWatermarkRecord:
    """Advance only after the corresponding collection completed without missed pages."""
    when = succeeded_at or datetime.now(UTC)
    record = get_watermark(session, connection_id, scope)
    if record is None:
        record = SyncWatermarkRecord(
            id=str(uuid4()),
            connection_id=connection_id,
            sync_scope=scope,
            last_successful_watermark=watermark,
            last_attempt_at=when,
            last_success_at=when,
        )
        session.add(record)
    else:
        record.last_successful_watermark = watermark
        record.last_success_at = when
    session.flush()
    return record


def effective_since(watermark: datetime | None, overlap_seconds: int) -> datetime | None:
    """Return a conservative lower bound. Prefer duplicate reads over missed records.

    Workable `updated_after` means "updated after" (exclusive of the exact instant)
    and official timestamps are often second-granularity. Subtracting a safety
    overlap covers clock skew and same-second updates.
    """
    if watermark is None:
        return None
    aware = watermark if watermark.tzinfo else watermark.replace(tzinfo=UTC)
    seconds = max(int(overlap_seconds), 0)
    return aware - timedelta(seconds=seconds)


def format_spi_timestamp(value: datetime) -> str:
    """Official Workable SPI input example: 20150708T115616Z (also accepts Unix time)."""
    aware = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
