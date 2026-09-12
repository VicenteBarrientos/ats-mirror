from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ApplicationStatus,
    AutomationRunStatus,
    EventType,
    JobStatus,
    SyncRunStatus,
)


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    title: str
    department: str | None = None
    location: str | None = None
    status: JobStatus
    description: str | None = None
    created_at: datetime
    candidate_count: int | None = None


class Candidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    name: str
    headline: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    current_stage: str | None = None
    created_at: datetime
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    social_links: list[dict[str, Any]] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    job_id: str | None = None
    job_title: str | None = None
    last_event_at: datetime | None = None
    last_event_type: EventType | None = None


class Application(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    candidate_id: str
    job_id: str
    stage: str | None = None
    status: ApplicationStatus = ApplicationStatus.ACTIVE
    created_at: datetime | None = None


class RecruitingEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    candidate_id: str | None = None
    job_id: str | None = None
    event_type: EventType
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class Stage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    job_id: str | None = None
    name: str
    position: int


class FileMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    candidate_id: str
    filename: str
    file_type: str | None = None
    source_ref: str | None = None
    created_at: datetime | None = None


class Member(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    name: str
    email: str | None = None
    role: str | None = None


class InterviewFeedback(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    candidate_id: str
    job_id: str | None = None
    interviewer: str | None = None
    summary: str
    submitted_at: datetime


class CandidateNote(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    body: str
    created_at: datetime
    dry_run: bool = False


class WritePreview(BaseModel):
    """Returned when DRY_RUN is on and a write was not sent to the ATS."""

    dry_run: bool = True
    action: str
    target: str
    message: str


class ProviderHealth(BaseModel):
    provider: str
    ok: bool
    message: str
    capabilities: list[str]
    dry_run: bool = False
    account_id: str | None = None
    account_name: str | None = None


class AutomationRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow: str
    provider: str
    entity_id: str | None = None
    status: AutomationRunStatus
    dry_run: bool
    started_at: datetime
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class AuditLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    provider: str
    actor: str
    target: str
    request_summary: str | None = None
    result: str | None = None
    created_at: datetime


class CandidateDetail(Candidate):
    applications: list[Application] = Field(default_factory=list)
    events: list[RecruitingEvent] = Field(default_factory=list)
    files: list[FileMetadata] = Field(default_factory=list)


class AtsConnection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    external_account_id: str | None = None
    account_name: str | None = None
    created_at: datetime
    updated_at: datetime


class SyncError(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sync_run_id: str
    provider: str
    object_type: str
    external_id: str | None = None
    error_type: str
    error_category: str = "runtime"
    http_status: int | None = None
    message: str
    timestamp: datetime


class SyncRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    connection_id: str | None = None
    connection_name: str | None = None
    provider: str
    sync_type: str
    started_at: datetime
    completed_at: datetime | None = None
    status: SyncRunStatus
    jobs_seen: int = 0
    candidates_seen: int = 0
    applications_seen: int = 0
    events_seen: int = 0
    stages_seen: int = 0
    files_seen: int = 0
    source_objects_fetched: int = 0
    raw_objects_created: int = 0
    raw_objects_updated: int = 0
    raw_objects_unchanged: int = 0
    canonical_records_created: int = 0
    canonical_records_updated: int = 0
    canonical_records_unchanged: int = 0
    created_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    error_count: int = 0
    error_summary: str | None = None
    errors: list[SyncError] = Field(default_factory=list)
