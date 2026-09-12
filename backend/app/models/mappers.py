from datetime import UTC, datetime
from typing import Any

from app.models.domain import (
    Application,
    Candidate,
    FileMetadata,
    Job,
    RecruitingEvent,
    Stage,
    SyncError,
    SyncRun,
)
from app.models.enums import ApplicationStatus, EventType, JobStatus, SyncRunStatus
from app.models.orm import (
    ApplicationRecord,
    CandidateRecord,
    EventRecord,
    FileMetadataRecord,
    JobRecord,
    StageRecord,
    SyncErrorRecord,
    SyncRunRecord,
)


def job_from_record(record: JobRecord) -> Job:
    return Job(
        id=record.id,
        external_id=record.external_id,
        title=record.title,
        department=record.department,
        location=record.location,
        status=JobStatus(record.status),
        description=record.description,
        created_at=_ensure_aware(record.created_at),
        candidate_count=record.candidate_count,
    )


def candidate_from_record(record: CandidateRecord) -> Candidate:
    return Candidate(
        id=record.id,
        external_id=record.external_id,
        name=record.name,
        headline=record.headline,
        location=record.location,
        email=record.email,
        phone=record.phone,
        current_stage=record.current_stage,
        created_at=_ensure_aware(record.created_at),
        summary=record.summary,
        skills=_as_str_list(record.skills),
        tags=_as_str_list(record.tags),
        source=record.source,
        social_links=_as_dict_list(record.social_links),
        experience=_as_dict_list(record.experience),
        education=_as_dict_list(record.education),
    )


def application_from_record(record: ApplicationRecord) -> Application:
    return Application(
        id=record.id,
        external_id=record.external_id,
        candidate_id=record.candidate_id,
        job_id=record.job_id,
        stage=record.stage,
        status=ApplicationStatus(record.status),
        created_at=_ensure_aware(record.created_at) if record.created_at else None,
    )


def event_from_record(record: EventRecord) -> RecruitingEvent:
    return RecruitingEvent(
        id=record.id,
        external_id=record.external_id,
        candidate_id=record.candidate_id,
        job_id=record.job_id,
        event_type=EventType(record.event_type),
        timestamp=_ensure_aware(record.timestamp),
        metadata=record.event_metadata or {},
    )


def stage_from_record(record: StageRecord) -> Stage:
    return Stage(
        id=record.id,
        external_id=record.external_id,
        job_id=record.job_id,
        name=record.name,
        position=record.position,
    )


def file_from_record(record: FileMetadataRecord) -> FileMetadata:
    return FileMetadata(
        id=record.id,
        external_id=record.external_id,
        candidate_id=record.candidate_id,
        filename=record.filename,
        file_type=record.file_type,
        source_ref=record.source_ref,
        created_at=_ensure_aware(record.created_at) if record.created_at else None,
    )


def sync_error_from_record(record: SyncErrorRecord) -> SyncError:
    return SyncError(
        id=record.id,
        sync_run_id=record.sync_run_id,
        provider=record.provider,
        object_type=record.object_type,
        external_id=record.external_id,
        error_type=record.error_type,
        error_category=record.error_category or "runtime",
        http_status=record.http_status,
        message=record.message,
        timestamp=_ensure_aware(record.timestamp),
    )


def _as_int(value: object) -> int:
    if value is None or isinstance(value, bool):
        return 0 if value is None else int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return 0


def sync_run_from_record(record: SyncRunRecord, *, include_errors: bool = False) -> SyncRun:
    jobs_seen = _as_int(record.jobs_seen)
    candidates_seen = _as_int(record.candidates_seen)
    applications_seen = _as_int(record.applications_seen)
    events_seen = _as_int(record.events_seen)
    stages_seen = _as_int(record.stages_seen)
    files_seen = _as_int(record.files_seen)
    created = _as_int(record.canonical_records_created) or _as_int(record.created_count)
    updated = _as_int(record.canonical_records_updated) or _as_int(record.updated_count)
    unchanged = _as_int(record.canonical_records_unchanged) or _as_int(record.unchanged_count)
    source_fetched = _as_int(record.source_objects_fetched) or (
        jobs_seen + candidates_seen + applications_seen + events_seen + stages_seen + files_seen
    )
    connection_name = None
    connection = getattr(record, "connection", None)
    if connection is not None:
        connection_name = connection.account_name or connection.external_account_id
    return SyncRun(
        id=record.id,
        connection_id=record.connection_id,
        connection_name=connection_name,
        provider=record.provider,
        sync_type=record.sync_type,
        started_at=_ensure_aware(record.started_at),
        completed_at=_ensure_aware(record.completed_at) if record.completed_at else None,
        status=SyncRunStatus(record.status),
        jobs_seen=jobs_seen,
        candidates_seen=candidates_seen,
        applications_seen=applications_seen,
        events_seen=events_seen,
        stages_seen=stages_seen,
        files_seen=files_seen,
        source_objects_fetched=source_fetched,
        raw_objects_created=_as_int(record.raw_objects_created),
        raw_objects_updated=_as_int(record.raw_objects_updated),
        raw_objects_unchanged=_as_int(record.raw_objects_unchanged),
        canonical_records_created=created,
        canonical_records_updated=updated,
        canonical_records_unchanged=unchanged,
        created_count=created,
        updated_count=updated,
        unchanged_count=unchanged,
        error_count=_as_int(record.error_count),
        error_summary=record.error_summary,
        errors=[sync_error_from_record(item) for item in record.errors] if include_errors else [],
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
