from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.domain import (
    Application,
    Candidate,
    CandidateDetail,
    Job,
    ProviderHealth,
    RecruitingEvent,
)
from app.models.enums import EventType
from app.models.mappers import (
    application_from_record,
    candidate_from_record,
    event_from_record,
    file_from_record,
    job_from_record,
)
from app.models.orm import (
    ApplicationRecord,
    CandidateRecord,
    JobRecord,
)
from app.providers.base import ATSProvider
from app.providers.errors import EntityNotFoundError
from app.sync.connections import get_or_create_connection


class RecruitingService:
    """Reads the local mirrored database. Does not call the ATS on page loads."""

    def __init__(self, session: Session, provider: ATSProvider) -> None:
        self.session = session
        self.provider = provider
        self.connection = get_or_create_connection(session, provider)

    def list_jobs(self, *, limit: int = 50, offset: int = 0) -> list[Job]:
        records = self.session.scalars(
            select(JobRecord)
            .where(JobRecord.connection_id == self.connection.id)
            .order_by(JobRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [job_from_record(record) for record in records]

    def get_job(self, job_id: str) -> Job:
        record = self._find_job_record(job_id)
        if record is None:
            raise EntityNotFoundError("job", job_id)
        return job_from_record(record)

    def list_candidates(
        self,
        job_id: str | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Candidate]:
        query = select(CandidateRecord).where(CandidateRecord.connection_id == self.connection.id)
        if job_id is not None:
            job_record = self._find_job_record(job_id)
            if job_record is None:
                raise EntityNotFoundError("job", job_id)
            linked_ids = select(ApplicationRecord.candidate_id).where(
                ApplicationRecord.job_id == job_record.id
            )
            query = query.where(CandidateRecord.id.in_(linked_ids))
        records = self.session.scalars(
            query.order_by(CandidateRecord.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return [self._with_list_context(record) for record in records]

    def get_candidate(self, candidate_id: str) -> CandidateDetail:
        record = self._find_candidate_record(candidate_id)
        if record is None:
            raise EntityNotFoundError("candidate", candidate_id)
        applications = [
            application_from_record(item)
            for item in sorted(record.applications, key=lambda item: item.id)
        ]
        events = [
            event_from_record(item)
            for item in sorted(record.events, key=lambda item: item.timestamp)
        ]
        files = [file_from_record(item) for item in record.files]
        stored = self._with_list_context(record)
        return CandidateDetail(
            **{
                **stored.model_dump(),
                "applications": applications,
                "events": events,
                "files": files,
            }
        )

    def provider_health(self) -> ProviderHealth:
        return self.provider.health_check()

    def export_candidate_rows(self) -> list[dict[str, str]]:
        records = self.session.scalars(
            select(CandidateRecord)
            .options(selectinload(CandidateRecord.applications))
            .where(CandidateRecord.connection_id == self.connection.id)
            .order_by(CandidateRecord.created_at.desc())
        ).all()
        rows: list[dict[str, str]] = []
        account = self.connection.account_name or self.connection.external_account_id or ""
        for record in records:
            applications = [application_from_record(item) for item in record.applications]
            _job_id, job_title = self._job_from_applications(applications)
            rows.append(
                {
                    "provider": record.provider,
                    "connection": account,
                    "external_candidate_id": record.external_id,
                    "name": record.name,
                    "email": record.email or "",
                    "phone": record.phone or "",
                    "headline": record.headline or "",
                    "location": record.location or "",
                    "current_job": job_title or "",
                    "stage": record.current_stage or "",
                    "source": record.source or "",
                    "tags": ", ".join(item for item in record.tags or [] if isinstance(item, str)),
                    "created_at": _iso(record.created_at),
                    "source_updated_at": _iso(record.source_updated_at),
                    "last_synced_at": _iso(record.last_synced_at),
                }
            )
        return rows

    def _with_list_context(self, record: CandidateRecord) -> Candidate:
        stored = candidate_from_record(record)
        applications = [application_from_record(item) for item in record.applications]
        events = [event_from_record(item) for item in record.events]
        job_id, job_title = self._job_from_applications(applications)
        last_event_at, last_event_type = self._latest_event(events)
        return stored.model_copy(
            update={
                "job_id": job_id,
                "job_title": job_title,
                "last_event_at": last_event_at,
                "last_event_type": last_event_type,
            }
        )

    def _job_from_applications(self, applications: list[Application]) -> tuple[str | None, str | None]:
        if not applications:
            return None, None
        job_record = self.session.get(JobRecord, applications[0].job_id)
        if job_record is not None:
            return job_record.id, job_record.title
        return applications[0].job_id, None

    @staticmethod
    def _latest_event(
        events: list[RecruitingEvent],
    ) -> tuple[datetime | None, EventType | None]:
        if not events:
            return None, None
        latest = max(events, key=lambda event: event.timestamp)
        return latest.timestamp, latest.event_type

    def _find_job_record(self, job_id: str) -> JobRecord | None:
        record = self.session.get(JobRecord, job_id)
        if record is not None:
            return record
        return self.session.scalar(
            select(JobRecord).where(
                JobRecord.connection_id == self.connection.id,
                JobRecord.external_id == job_id,
            )
        )

    def _find_candidate_record(self, candidate_id: str) -> CandidateRecord | None:
        record = self.session.get(CandidateRecord, candidate_id)
        if record is not None:
            return record
        return self.session.scalar(
            select(CandidateRecord).where(
                CandidateRecord.connection_id == self.connection.id,
                CandidateRecord.external_id == candidate_id,
            )
        )


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()
