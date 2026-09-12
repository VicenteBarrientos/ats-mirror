from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from functools import partial
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.domain import (
    Application,
    Candidate,
    FileMetadata,
    Job,
    RecruitingEvent,
    Stage,
    SyncRun,
)
from app.models.enums import Capability, SyncRunStatus
from app.models.mappers import sync_run_from_record
from app.models.orm import (
    ApplicationRecord,
    AtsConnectionRecord,
    CandidateRecord,
    EventRecord,
    FileMetadataRecord,
    JobRecord,
    RawATSObjectRecord,
    StageRecord,
    SyncErrorRecord,
    SyncRunRecord,
)
from app.providers.base import ATSProvider
from app.providers.errors import (
    EntityNotFoundError,
    ProviderConfigError,
    ProviderUnavailableError,
    UnsupportedCapabilityError,
)
from app.providers.pagination import iter_offset_pages
from app.sync.connections import get_or_create_connection
from app.sync.hashing import canonical_content_hash, raw_content_hash
from app.sync.watermarks import (
    INCREMENTAL_SCOPES,
    SCOPE_CANDIDATES,
    SCOPE_EVENTS,
    SCOPE_JOBS,
    SCOPE_MIRROR,
    advance_watermark,
    effective_since,
    get_watermark,
    list_watermarks,
    mark_attempt,
)

logger = logging.getLogger(__name__)

_PAGE_SIZE = 50
_BEARER = re.compile(r"Bearer\s+\S+", re.IGNORECASE)


class SyncService:
    """Read from ATSProvider, persist raw + normalized rows locally. Never writes to the ATS."""

    def __init__(self, session: Session, provider: ATSProvider) -> None:
        self.session = session
        self.provider = provider
        self.connection: AtsConnectionRecord = get_or_create_connection(session, provider)
        self._run: SyncRunRecord | None = None
        self._mode = "full"
        self._collection_failed: set[str] = set()
        self._scope_errors: dict[str, int] = {}
        self._fetched_candidate_ids: set[str] = set()

    @property
    def connection_id(self) -> str:
        return self.connection.id

    def sync_all(self) -> SyncRun:
        return self._execute("full", self._sync_full)

    def sync_incremental(self) -> SyncRun:
        jobs_wm = get_watermark(self.session, self.connection_id, SCOPE_JOBS)
        candidates_wm = get_watermark(self.session, self.connection_id, SCOPE_CANDIDATES)
        if jobs_wm is None or candidates_wm is None or jobs_wm.last_successful_watermark is None:
            return self.sync_all()
        if candidates_wm.last_successful_watermark is None:
            return self.sync_all()
        return self._execute("incremental", self._sync_incremental)

    def sync_jobs(self) -> SyncRun:
        return self._execute("jobs", self._sync_jobs)

    def sync_candidates(self) -> SyncRun:
        return self._execute("candidates", self._sync_candidates_bundle)

    def sync_applications(self) -> SyncRun:
        return self._execute("applications", self._sync_applications)

    def sync_events(self) -> SyncRun:
        return self._execute("events", self._sync_events)

    def latest_run(self) -> SyncRun | None:
        record = self.session.scalar(
            select(SyncRunRecord)
            .options(selectinload(SyncRunRecord.connection))
            .where(SyncRunRecord.connection_id == self.connection_id)
            .order_by(SyncRunRecord.started_at.desc())
        )
        if record is None:
            return None
        return sync_run_from_record(record)

    def get_run(self, run_id: str) -> SyncRun | None:
        record = self.session.scalar(
            select(SyncRunRecord)
            .options(selectinload(SyncRunRecord.errors), selectinload(SyncRunRecord.connection))
            .where(SyncRunRecord.id == run_id)
        )
        if record is None:
            return None
        return sync_run_from_record(record, include_errors=True)

    def list_runs(self, *, limit: int = 50) -> list[SyncRun]:
        records = self.session.scalars(
            select(SyncRunRecord)
            .options(selectinload(SyncRunRecord.connection))
            .where(SyncRunRecord.connection_id == self.connection_id)
            .order_by(SyncRunRecord.started_at.desc())
            .limit(limit)
        ).all()
        return [sync_run_from_record(record) for record in records]

    def latest_successful_at(self, sync_type: str | None = None) -> datetime | None:
        query = (
            select(SyncRunRecord)
            .where(
                SyncRunRecord.connection_id == self.connection_id,
                SyncRunRecord.status.in_(
                    (SyncRunStatus.COMPLETED.value, SyncRunStatus.COMPLETED_WITH_ERRORS.value)
                ),
            )
            .order_by(SyncRunRecord.completed_at.desc())
        )
        if sync_type is not None:
            query = query.where(SyncRunRecord.sync_type == sync_type)
        record = self.session.scalar(query)
        if record is None or record.completed_at is None:
            return None
        return record.completed_at

    def watermark_status(self) -> dict[str, dict[str, str | None]]:
        rows = list_watermarks(self.session, self.connection_id)
        status: dict[str, dict[str, str | None]] = {}
        for scope in (*INCREMENTAL_SCOPES, SCOPE_MIRROR):
            row = rows.get(scope)
            status[scope] = {
                "last_successful_watermark": (
                    row.last_successful_watermark.isoformat()
                    if row is not None and row.last_successful_watermark is not None
                    else None
                ),
                "last_attempt_at": (
                    row.last_attempt_at.isoformat() if row is not None and row.last_attempt_at else None
                ),
                "last_success_at": (
                    row.last_success_at.isoformat() if row is not None and row.last_success_at else None
                ),
            }
        return status

    def mirror_counts(self) -> dict[str, int]:
        cid = self.connection_id
        return {
            "jobs": self._count(JobRecord, cid),
            "candidates": self._count(CandidateRecord, cid),
            "applications": self._count(ApplicationRecord, cid),
            "events": self._count(EventRecord, cid),
            "stages": self._count(StageRecord, cid),
            "files": self._count(FileMetadataRecord, cid),
            "raw_objects": self._count(RawATSObjectRecord, cid),
        }

    def _count(self, model: type[Any], connection_id: str) -> int:
        value = self.session.scalar(
            select(func.count()).select_from(model).where(model.connection_id == connection_id)
        )
        return int(value or 0)

    def _execute(self, sync_type: str, body: Callable[[], None]) -> SyncRun:
        run = SyncRunRecord(
            id=str(uuid4()),
            connection_id=self.connection_id,
            provider=self.provider.name,
            sync_type=sync_type,
            started_at=datetime.now(UTC),
            completed_at=None,
            status=SyncRunStatus.RUNNING.value,
            jobs_seen=0,
            candidates_seen=0,
            applications_seen=0,
            events_seen=0,
            stages_seen=0,
            files_seen=0,
            source_objects_fetched=0,
            raw_objects_created=0,
            raw_objects_updated=0,
            raw_objects_unchanged=0,
            canonical_records_created=0,
            canonical_records_updated=0,
            canonical_records_unchanged=0,
            created_count=0,
            updated_count=0,
            unchanged_count=0,
            error_count=0,
            error_summary=None,
        )
        self.session.add(run)
        self.session.flush()
        self._run = run
        self._collection_failed = set()
        self._scope_errors = {}
        self._fetched_candidate_ids = set()
        try:
            body()
            self._refresh_job_candidate_counts()
            run.source_objects_fetched = (
                run.jobs_seen
                + run.candidates_seen
                + run.applications_seen
                + run.events_seen
                + run.stages_seen
                + run.files_seen
            )
            if run.error_count:
                run.status = SyncRunStatus.COMPLETED_WITH_ERRORS.value
                run.error_summary = f"{run.error_count} object(s) failed during sync."
            else:
                run.status = SyncRunStatus.COMPLETED.value
            self._advance_successful_watermarks(run)
        except Exception as exc:
            run.status = SyncRunStatus.FAILED.value
            run.error_summary = _safe_message(str(exc))
            self._record_error("sync", None, exc)
            logger.info(
                "Sync failed",
                extra={"extra_fields": {"sync_run_id": run.id, "provider": self.provider.name}},
            )
        run.completed_at = datetime.now(UTC)
        self.session.flush()
        loaded = self.session.scalar(
            select(SyncRunRecord)
            .options(selectinload(SyncRunRecord.errors), selectinload(SyncRunRecord.connection))
            .where(SyncRunRecord.id == run.id)
        )
        assert loaded is not None
        logger.info(
            "Sync finished",
            extra={
                "extra_fields": {
                    "sync_run_id": run.id,
                    "provider": self.provider.name,
                    "connection_id": self.connection_id,
                    "status": run.status,
                    "source_objects_fetched": run.source_objects_fetched,
                    "canonical_created": run.canonical_records_created,
                    "canonical_updated": run.canonical_records_updated,
                    "canonical_unchanged": run.canonical_records_unchanged,
                    "errors": run.error_count,
                }
            },
        )
        return sync_run_from_record(loaded, include_errors=True)

    def _sync_full(self) -> None:
        self._mode = "full"
        self._begin_watermark_attempts()
        self._sync_jobs()
        self._sync_stages()
        fetched = self._sync_candidates()
        self._fetched_candidate_ids = fetched
        self._sync_applications()
        self._sync_events()
        self._sync_files()

    def _sync_incremental(self) -> None:
        self._mode = "incremental"
        overlap = get_settings().incremental_overlap_seconds
        self._begin_watermark_attempts()
        jobs_since = effective_since(self._watermark_value(SCOPE_JOBS), overlap)
        candidates_since = effective_since(self._watermark_value(SCOPE_CANDIDATES), overlap)
        events_since = effective_since(
            self._watermark_value(SCOPE_EVENTS) or self._watermark_value(SCOPE_CANDIDATES),
            overlap,
        )
        self._sync_jobs(updated_after=jobs_since)
        self._sync_stages()
        fetched = self._sync_candidates(updated_after=candidates_since)
        self._fetched_candidate_ids = fetched
        self._sync_applications(candidate_external_ids=fetched)
        self._sync_events(updated_after=events_since)
        self._sync_files(candidate_external_ids=fetched)

    def _sync_candidates_bundle(self) -> None:
        fetched = self._sync_candidates()
        self._fetched_candidate_ids = fetched
        self._sync_applications()
        self._sync_events()
        self._sync_files()

    def _sync_jobs(self, *, updated_after: datetime | None = None) -> None:
        seen: set[str] = set()
        try:
            for job in self._iter_jobs(updated_after=updated_after):
                seen.add(job.external_id)
                self._safe("job", job.external_id, partial(self._ingest_job, job))
            if self._mode == "full" and "jobs" not in self._collection_failed:
                self._mark_missing(JobRecord, seen)
        except Exception as exc:
            self._collection_failed.add("jobs")
            self._record_error("job", None, exc)

    def _sync_stages(self) -> None:
        if Capability.READ_STAGES not in self.provider.capabilities:
            return
        seen: set[str] = set()
        try:
            for stage in self.provider.get_stages(None):
                if stage.external_id in seen:
                    continue
                seen.add(stage.external_id)
                self._safe("stage", stage.external_id, partial(self._ingest_stage, stage))
        except UnsupportedCapabilityError:
            return
        except Exception as exc:
            self._collection_failed.add("stages")
            self._record_error("stage", None, exc)
        jobs = self.session.scalars(
            select(JobRecord).where(JobRecord.connection_id == self.connection_id)
        ).all()
        for job in jobs:
            try:
                for stage in self.provider.get_stages(job.external_id):
                    if stage.external_id in seen:
                        continue
                    seen.add(stage.external_id)
                    self._safe("stage", stage.external_id, partial(self._ingest_stage, stage))
            except UnsupportedCapabilityError:
                return
            except Exception as exc:
                self._record_error("stage", job.external_id, exc)
        if self._mode == "full" and "stages" not in self._collection_failed:
            self._mark_missing(StageRecord, seen)

    def _sync_candidates(self, *, updated_after: datetime | None = None) -> set[str]:
        fetched: set[str] = set()
        try:
            for candidate in self._iter_candidates(updated_after=updated_after):
                fetched.add(candidate.external_id)
                self._safe(
                    "candidate",
                    candidate.external_id,
                    partial(self._ingest_candidate, candidate),
                )
            if self._mode == "full" and "candidates" not in self._collection_failed:
                self._mark_missing(CandidateRecord, fetched)
        except Exception as exc:
            self._collection_failed.add("candidates")
            self._record_error("candidate", None, exc)
        return fetched

    def _sync_applications(self, *, candidate_external_ids: set[str] | None = None) -> None:
        candidates = self.session.scalars(
            select(CandidateRecord).where(CandidateRecord.connection_id == self.connection_id)
        ).all()
        if candidate_external_ids is not None:
            candidates = [
                candidate for candidate in candidates if candidate.external_id in candidate_external_ids
            ]
        for candidate in candidates:
            try:
                applications = self.provider.get_candidate_applications(candidate.external_id)
            except UnsupportedCapabilityError:
                return
            except Exception as exc:
                self._record_error("application", candidate.external_id, exc)
                continue
            for application in applications:
                self._safe(
                    "application",
                    application.external_id,
                    partial(self._ingest_application, application),
                )

    def _sync_events(self, *, updated_after: datetime | None = None) -> None:
        if Capability.READ_EVENTS not in self.provider.capabilities:
            return
        candidates = self.session.scalars(
            select(CandidateRecord).where(CandidateRecord.connection_id == self.connection_id)
        ).all()
        for candidate in candidates:
            try:
                events = self._provider_events(candidate.external_id, updated_after=updated_after)
            except UnsupportedCapabilityError:
                return
            except Exception as exc:
                self._record_error("event", candidate.external_id, exc)
                continue
            for event in events:
                self._safe("event", event.external_id, partial(self._ingest_event, event))

    def _sync_files(self, *, candidate_external_ids: set[str] | None = None) -> None:
        if Capability.READ_FILES_METADATA not in self.provider.capabilities:
            return
        candidates = self.session.scalars(
            select(CandidateRecord).where(CandidateRecord.connection_id == self.connection_id)
        ).all()
        if candidate_external_ids is not None:
            candidates = [
                candidate for candidate in candidates if candidate.external_id in candidate_external_ids
            ]
        for candidate in candidates:
            try:
                files = self.provider.list_candidate_files(candidate.external_id)
            except UnsupportedCapabilityError:
                return
            except Exception as exc:
                self._record_error("file", candidate.external_id, exc)
                continue
            for file_meta in files:
                self._safe("file", file_meta.external_id, partial(self._ingest_file, file_meta))

    def _iter_jobs(self, *, updated_after: datetime | None = None) -> Iterator[Job]:
        iterator = getattr(self.provider, "iter_jobs", None)
        if callable(iterator):
            yield from iterator(page_size=_PAGE_SIZE, updated_after=updated_after)
            return
        yield from iter_offset_pages(self.provider.list_jobs, page_size=_PAGE_SIZE)

    def _iter_candidates(self, *, updated_after: datetime | None = None) -> Iterator[Candidate]:
        iterator = getattr(self.provider, "iter_candidates", None)
        if callable(iterator):
            yield from iterator(page_size=_PAGE_SIZE, updated_after=updated_after)
            return
        yield from iter_offset_pages(self.provider.list_candidates, page_size=_PAGE_SIZE)

    def _provider_events(
        self, candidate_id: str, *, updated_after: datetime | None
    ) -> list[RecruitingEvent]:
        return self.provider.get_candidate_events(candidate_id, updated_after=updated_after)

    def _ingest_job(self, job: Job) -> None:
        self._bump("jobs_seen")
        raw = self._raw_payload("job", job.external_id, job.model_dump(mode="json"))
        outcome = self._mirror(
            object_type="job",
            external_id=job.external_id,
            raw=raw,
            canonical_digest=canonical_content_hash("job", job),
            source_updated=_timestamp_from_raw(raw),
        )
        record = self._find_job(job.external_id)
        if outcome == "raw_unchanged" and record is not None:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
            return
        now = datetime.now(UTC)
        source_updated = _timestamp_from_raw(raw)
        digest = canonical_content_hash("job", job)
        if record is None:
            record = JobRecord(
                id=str(uuid4()),
                connection_id=self.connection_id,
                provider=self.provider.name,
                external_id=job.external_id,
                title=job.title,
                department=job.department,
                location=job.location,
                status=job.status.value,
                description=job.description,
                candidate_count=job.candidate_count,
                created_at=job.created_at,
                updated_at=source_updated,
                source_updated_at=source_updated,
                synced_at=now,
                last_synced_at=now,
                last_seen_at=now,
                source_status="present",
                content_hash=digest,
            )
            self.session.add(record)
            self._mark_canonical_created()
        elif record.content_hash == digest:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
        else:
            record.title = job.title
            record.department = job.department
            record.location = job.location
            record.status = job.status.value
            record.description = job.description
            record.created_at = job.created_at
            record.updated_at = source_updated
            record.source_updated_at = source_updated
            record.synced_at = now
            record.last_synced_at = now
            record.last_seen_at = now
            record.source_status = "present"
            record.content_hash = digest
            self._mark_canonical_updated()
        self.session.flush()

    def _ingest_candidate(self, candidate: Candidate) -> None:
        self._bump("candidates_seen")
        raw = self._raw_payload("candidate", candidate.external_id, candidate.model_dump(mode="json"))
        outcome = self._mirror(
            object_type="candidate",
            external_id=candidate.external_id,
            raw=raw,
            canonical_digest=canonical_content_hash("candidate", candidate),
            source_updated=_timestamp_from_raw(raw),
        )
        record = self._find_candidate(candidate.external_id)
        if outcome == "raw_unchanged" and record is not None:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
            return
        now = datetime.now(UTC)
        source_updated = _timestamp_from_raw(raw)
        digest = canonical_content_hash("candidate", candidate)
        if record is None:
            record = CandidateRecord(
                id=str(uuid4()),
                connection_id=self.connection_id,
                provider=self.provider.name,
                external_id=candidate.external_id,
                name=candidate.name,
                headline=candidate.headline,
                location=candidate.location,
                email=candidate.email,
                phone=candidate.phone,
                current_stage=candidate.current_stage,
                summary=candidate.summary,
                skills=candidate.skills,
                tags=candidate.tags,
                source=candidate.source,
                social_links=candidate.social_links,
                experience=candidate.experience,
                education=candidate.education,
                created_at=candidate.created_at,
                updated_at=source_updated,
                source_updated_at=source_updated,
                synced_at=now,
                last_synced_at=now,
                last_seen_at=now,
                source_status="present",
                content_hash=digest,
            )
            self.session.add(record)
            self._mark_canonical_created()
        elif record.content_hash == digest:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
        else:
            record.name = candidate.name
            record.headline = candidate.headline
            record.location = candidate.location
            record.email = candidate.email
            record.phone = candidate.phone
            record.current_stage = candidate.current_stage
            record.summary = candidate.summary
            record.skills = candidate.skills
            record.tags = candidate.tags
            record.source = candidate.source
            record.social_links = candidate.social_links
            record.experience = candidate.experience
            record.education = candidate.education
            record.created_at = candidate.created_at
            record.updated_at = source_updated
            record.source_updated_at = source_updated
            record.synced_at = now
            record.last_synced_at = now
            record.last_seen_at = now
            record.source_status = "present"
            record.content_hash = digest
            self._mark_canonical_updated()
        self.session.flush()

    def _ingest_application(self, application: Application) -> None:
        self._bump("applications_seen")
        raw = self._raw_payload(
            "application", application.external_id, application.model_dump(mode="json")
        )
        outcome = self._mirror(
            object_type="application",
            external_id=application.external_id,
            raw=raw,
            canonical_digest=canonical_content_hash("application", application),
            source_updated=_timestamp_from_raw(raw) or application.created_at,
        )
        candidate = self._find_candidate(application.candidate_id)
        job = self._find_job(application.job_id)
        if candidate is None or job is None:
            raise ValueError(
                f"Application '{application.external_id}' is missing a mirrored parent "
                f"(candidate={application.candidate_id}, job={application.job_id})."
            )
        record = self.session.scalar(
            select(ApplicationRecord).where(
                ApplicationRecord.connection_id == self.connection_id,
                ApplicationRecord.external_id == application.external_id,
            )
        )
        if outcome == "raw_unchanged" and record is not None:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
            return
        now = datetime.now(UTC)
        source_updated = _timestamp_from_raw(raw) or application.created_at
        digest = canonical_content_hash("application", application)
        if record is None:
            record = ApplicationRecord(
                id=str(uuid4()),
                connection_id=self.connection_id,
                provider=self.provider.name,
                external_id=application.external_id,
                candidate_id=candidate.id,
                job_id=job.id,
                stage=application.stage,
                status=application.status.value,
                created_at=application.created_at,
                updated_at=source_updated,
                source_updated_at=source_updated,
                last_synced_at=now,
                last_seen_at=now,
                source_status="present",
                content_hash=digest,
            )
            self.session.add(record)
            self._mark_canonical_created()
        elif record.content_hash == digest:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
        else:
            record.candidate_id = candidate.id
            record.job_id = job.id
            record.stage = application.stage
            record.status = application.status.value
            record.created_at = application.created_at
            record.updated_at = source_updated
            record.source_updated_at = source_updated
            record.last_synced_at = now
            record.last_seen_at = now
            record.source_status = "present"
            record.content_hash = digest
            self._mark_canonical_updated()
        self.session.flush()

    def _ingest_event(self, event: RecruitingEvent) -> None:
        self._bump("events_seen")
        raw = self._raw_payload("event", event.external_id, event.model_dump(mode="json"))
        outcome = self._mirror(
            object_type="event",
            external_id=event.external_id,
            raw=raw,
            canonical_digest=canonical_content_hash("event", event),
            source_updated=event.timestamp,
        )
        record = self.session.scalar(
            select(EventRecord).where(
                EventRecord.connection_id == self.connection_id,
                EventRecord.external_id == event.external_id,
            )
        )
        if outcome == "raw_unchanged" and record is not None:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
            return
        candidate = self._find_candidate(event.candidate_id) if event.candidate_id else None
        job = self._find_job(event.job_id) if event.job_id else None
        now = datetime.now(UTC)
        digest = canonical_content_hash("event", event)
        if record is None:
            record = EventRecord(
                id=str(uuid4()),
                connection_id=self.connection_id,
                provider=self.provider.name,
                external_id=event.external_id,
                candidate_id=candidate.id if candidate else None,
                job_id=job.id if job else None,
                event_type=event.event_type.value,
                timestamp=event.timestamp,
                event_metadata=event.metadata,
                source_updated_at=event.timestamp,
                last_synced_at=now,
                last_seen_at=now,
                source_status="present",
                content_hash=digest,
            )
            self.session.add(record)
            self._mark_canonical_created()
        elif record.content_hash == digest:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
        else:
            record.event_type = event.event_type.value
            record.timestamp = event.timestamp
            record.event_metadata = event.metadata
            record.candidate_id = candidate.id if candidate else record.candidate_id
            record.job_id = job.id if job else record.job_id
            record.source_updated_at = event.timestamp
            record.last_synced_at = now
            record.last_seen_at = now
            record.source_status = "present"
            record.content_hash = digest
            self._mark_canonical_updated()
        self.session.flush()

    def _ingest_stage(self, stage: Stage) -> None:
        self._bump("stages_seen")
        raw = self._raw_payload("stage", stage.external_id, stage.model_dump(mode="json"))
        outcome = self._mirror(
            object_type="stage",
            external_id=stage.external_id,
            raw=raw,
            canonical_digest=canonical_content_hash("stage", stage),
            source_updated=None,
        )
        record = self.session.scalar(
            select(StageRecord).where(
                StageRecord.connection_id == self.connection_id,
                StageRecord.external_id == stage.external_id,
            )
        )
        if outcome == "raw_unchanged" and record is not None:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
            return
        job = self._find_job(stage.job_id) if stage.job_id else None
        now = datetime.now(UTC)
        digest = canonical_content_hash("stage", stage)
        if record is None:
            record = StageRecord(
                id=str(uuid4()),
                connection_id=self.connection_id,
                provider=self.provider.name,
                external_id=stage.external_id,
                job_id=job.id if job else None,
                name=stage.name,
                position=stage.position,
                last_synced_at=now,
                last_seen_at=now,
                source_status="present",
                content_hash=digest,
            )
            self.session.add(record)
            self._mark_canonical_created()
        elif record.content_hash == digest:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
        else:
            record.job_id = job.id if job else record.job_id
            record.name = stage.name
            record.position = stage.position
            record.last_synced_at = now
            record.last_seen_at = now
            record.source_status = "present"
            record.content_hash = digest
            self._mark_canonical_updated()
        self.session.flush()

    def _ingest_file(self, file_meta: FileMetadata) -> None:
        self._bump("files_seen")
        raw = self._raw_payload("file", file_meta.external_id, file_meta.model_dump(mode="json"))
        outcome = self._mirror(
            object_type="file",
            external_id=file_meta.external_id,
            raw=raw,
            canonical_digest=canonical_content_hash("file", file_meta),
            source_updated=file_meta.created_at,
        )
        record = self.session.scalar(
            select(FileMetadataRecord).where(
                FileMetadataRecord.connection_id == self.connection_id,
                FileMetadataRecord.external_id == file_meta.external_id,
            )
        )
        if outcome == "raw_unchanged" and record is not None:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
            return
        candidate = self._find_candidate(file_meta.candidate_id)
        if candidate is None:
            raise ValueError(f"File '{file_meta.external_id}' is missing mirrored candidate.")
        now = datetime.now(UTC)
        digest = canonical_content_hash("file", file_meta)
        if record is None:
            record = FileMetadataRecord(
                id=str(uuid4()),
                connection_id=self.connection_id,
                provider=self.provider.name,
                external_id=file_meta.external_id,
                candidate_id=candidate.id,
                filename=file_meta.filename,
                file_type=file_meta.file_type,
                source_ref=file_meta.source_ref,
                created_at=file_meta.created_at,
                last_synced_at=now,
                last_seen_at=now,
                source_status="present",
                content_hash=digest,
            )
            self.session.add(record)
            self._mark_canonical_created()
        elif record.content_hash == digest:
            self._touch_seen(record)
            self._mark_canonical_unchanged()
        else:
            record.candidate_id = candidate.id
            record.filename = file_meta.filename
            record.file_type = file_meta.file_type
            record.source_ref = file_meta.source_ref
            record.created_at = file_meta.created_at
            record.last_synced_at = now
            record.last_seen_at = now
            record.source_status = "present"
            record.content_hash = digest
            self._mark_canonical_updated()
        self.session.flush()

    def _mirror(
        self,
        *,
        object_type: str,
        external_id: str,
        raw: dict[str, Any],
        canonical_digest: str,
        source_updated: datetime | None,
    ) -> str:
        del canonical_digest
        digest = raw_content_hash(raw)
        record = self.session.scalar(
            select(RawATSObjectRecord).where(
                RawATSObjectRecord.connection_id == self.connection_id,
                RawATSObjectRecord.object_type == object_type,
                RawATSObjectRecord.external_id == external_id,
            )
        )
        now = datetime.now(UTC)
        if record is not None and record.content_hash == digest:
            record.last_seen_at = now
            self._mark_raw_unchanged()
            self.session.flush()
            return "raw_unchanged"
        if record is None:
            record = RawATSObjectRecord(
                id=str(uuid4()),
                connection_id=self.connection_id,
                provider=self.provider.name,
                object_type=object_type,
                external_id=external_id,
                raw_payload_json=raw,
                source_updated_at=source_updated,
                fetched_at=now,
                last_seen_at=now,
                content_hash=digest,
            )
            self.session.add(record)
            self._mark_raw_created()
            self.session.flush()
            return "raw_created"
        record.raw_payload_json = raw
        record.source_updated_at = source_updated
        record.fetched_at = now
        record.last_seen_at = now
        record.content_hash = digest
        self._mark_raw_updated()
        self.session.flush()
        return "raw_updated"

    def _refresh_job_candidate_counts(self) -> None:
        jobs = self.session.scalars(
            select(JobRecord).where(JobRecord.connection_id == self.connection_id)
        ).all()
        for job in jobs:
            count = self.session.scalar(
                select(func.count())
                .select_from(ApplicationRecord)
                .where(ApplicationRecord.job_id == job.id)
            )
            job.candidate_count = int(count or 0)

    def _raw_payload(self, object_type: str, external_id: str, fallback: dict[str, Any]) -> dict[str, Any]:
        consume = getattr(self.provider, "consume_raw", None)
        if callable(consume):
            peeked = consume(object_type, external_id)
            if isinstance(peeked, dict):
                return peeked
        return fallback

    def _touch_seen(self, record: Any) -> None:
        now = datetime.now(UTC)
        if hasattr(record, "last_seen_at"):
            record.last_seen_at = now
        if hasattr(record, "source_status"):
            record.source_status = "present"

    def _safe(self, object_type: str, external_id: str | None, action: Callable[[], None]) -> None:
        try:
            action()
        except Exception as exc:
            self._record_error(object_type, external_id, exc)

    def _begin_watermark_attempts(self) -> None:
        run = self._run
        if run is None:
            return
        when = run.started_at
        for scope in (*INCREMENTAL_SCOPES, SCOPE_MIRROR):
            mark_attempt(self.session, self.connection_id, scope, when)

    def _watermark_value(self, scope: str) -> datetime | None:
        record = get_watermark(self.session, self.connection_id, scope)
        if record is None:
            return None
        return record.last_successful_watermark

    def _advance_successful_watermarks(self, run: SyncRunRecord) -> None:
        if run.status == SyncRunStatus.FAILED.value:
            return
        when = run.started_at
        succeeded_at = run.completed_at or datetime.now(UTC)
        if self._scope_ok(SCOPE_JOBS, "job"):
            advance_watermark(self.session, self.connection_id, SCOPE_JOBS, when, succeeded_at=succeeded_at)
        if self._scope_ok(SCOPE_CANDIDATES, "candidate", "application"):
            advance_watermark(
                self.session, self.connection_id, SCOPE_CANDIDATES, when, succeeded_at=succeeded_at
            )
        if self._scope_ok(SCOPE_EVENTS, "event"):
            advance_watermark(self.session, self.connection_id, SCOPE_EVENTS, when, succeeded_at=succeeded_at)
        if run.status == SyncRunStatus.COMPLETED.value:
            advance_watermark(self.session, self.connection_id, SCOPE_MIRROR, when, succeeded_at=succeeded_at)

    def _scope_ok(self, collection: str, *object_types: str) -> bool:
        if collection in self._collection_failed:
            return False
        return all(self._scope_errors.get(name, 0) == 0 for name in object_types)

    def _mark_missing(self, model: type[Any], seen: set[str]) -> None:
        rows = self.session.scalars(select(model).where(model.connection_id == self.connection_id)).all()
        for row in rows:
            if row.external_id in seen:
                continue
            if getattr(row, "source_status", None) != "missing_from_source":
                row.source_status = "missing_from_source"
        self.session.flush()

    def _record_error(self, object_type: str, external_id: str | None, exc: BaseException) -> None:
        run = self._run
        if run is None:
            return
        run.error_count += 1
        self._scope_errors[object_type] = self._scope_errors.get(object_type, 0) + 1
        status = getattr(exc, "status_code", None)
        http_status = status if isinstance(status, int) else None
        self.session.add(
            SyncErrorRecord(
                id=str(uuid4()),
                sync_run_id=run.id,
                connection_id=self.connection_id,
                provider=self.provider.name,
                object_type=object_type,
                external_id=external_id,
                error_type=type(exc).__name__,
                error_category=_error_category(exc),
                http_status=http_status,
                message=_safe_message(str(exc)),
                timestamp=datetime.now(UTC),
            )
        )
        logger.info(
            "Sync object failed",
            extra={
                "extra_fields": {
                    "sync_run_id": run.id,
                    "object_type": object_type,
                    "external_id": external_id,
                    "error_type": type(exc).__name__,
                    "error_category": _error_category(exc),
                    "http_status": http_status,
                }
            },
        )

    def _bump(self, field: str) -> None:
        run = self._run
        if run is None:
            return
        setattr(run, field, int(getattr(run, field)) + 1)

    def _mark_raw_created(self) -> None:
        if self._run is not None:
            self._run.raw_objects_created += 1

    def _mark_raw_updated(self) -> None:
        if self._run is not None:
            self._run.raw_objects_updated += 1

    def _mark_raw_unchanged(self) -> None:
        if self._run is not None:
            self._run.raw_objects_unchanged += 1

    def _mark_canonical_created(self) -> None:
        if self._run is not None:
            self._run.canonical_records_created += 1
            self._run.created_count += 1

    def _mark_canonical_updated(self) -> None:
        if self._run is not None:
            self._run.canonical_records_updated += 1
            self._run.updated_count += 1

    def _mark_canonical_unchanged(self) -> None:
        if self._run is not None:
            self._run.canonical_records_unchanged += 1
            self._run.unchanged_count += 1

    def _find_job(self, job_id: str | None) -> JobRecord | None:
        if not job_id:
            return None
        record = self.session.get(JobRecord, job_id)
        if record is not None:
            return record
        return self.session.scalar(
            select(JobRecord).where(
                JobRecord.connection_id == self.connection_id,
                JobRecord.external_id == job_id,
            )
        )

    def _find_candidate(self, candidate_id: str | None) -> CandidateRecord | None:
        if not candidate_id:
            return None
        record = self.session.get(CandidateRecord, candidate_id)
        if record is not None:
            return record
        return self.session.scalar(
            select(CandidateRecord).where(
                CandidateRecord.connection_id == self.connection_id,
                CandidateRecord.external_id == candidate_id,
            )
        )


def _timestamp_from_raw(raw: dict[str, Any]) -> datetime | None:
    for key in ("updated_at", "source_updated_at", "created_at"):
        value = raw.get(key)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, str) and value:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _safe_message(message: str) -> str:
    return _BEARER.sub("Bearer [redacted]", message)


def _error_category(exc: BaseException) -> str:
    if isinstance(exc, ProviderConfigError):
        return "auth"
    if isinstance(exc, EntityNotFoundError):
        return "not_found"
    if isinstance(exc, ProviderUnavailableError):
        status = getattr(exc, "status_code", None)
        if status == 429:
            return "rate_limit"
        if isinstance(status, int) and status >= 500:
            return "http_server"
        if isinstance(status, int) and status >= 400:
            return "http_client"
        return "unavailable"
    if isinstance(exc, ValueError):
        return "validation"
    return "runtime"
