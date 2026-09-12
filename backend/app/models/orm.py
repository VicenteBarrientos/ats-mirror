from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class AtsConnectionRecord(Base):
    __tablename__ = "ats_connections"
    __table_args__ = (
        UniqueConstraint("provider", "external_account_id", name="uq_ats_connections_provider_account"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    jobs: Mapped[list[JobRecord]] = relationship(back_populates="connection")
    candidates: Mapped[list[CandidateRecord]] = relationship(back_populates="connection")
    sync_runs: Mapped[list[SyncRunRecord]] = relationship(back_populates="connection")


class JobRecord(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id", name="uq_jobs_connection_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(512))
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_status: Mapped[str] = mapped_column(String(32), default="present")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    connection: Mapped[AtsConnectionRecord] = relationship(back_populates="jobs")
    applications: Mapped[list[ApplicationRecord]] = relationship(back_populates="job")


class CandidateRecord(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id", name="uq_candidates_connection_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    headline: Mapped[str | None] = mapped_column(String(512), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    social_links: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    experience: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    education: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_status: Mapped[str] = mapped_column(String(32), default="present")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    connection: Mapped[AtsConnectionRecord] = relationship(back_populates="candidates")
    applications: Mapped[list[ApplicationRecord]] = relationship(back_populates="candidate")
    events: Mapped[list[EventRecord]] = relationship(back_populates="candidate")
    files: Mapped[list[FileMetadataRecord]] = relationship(back_populates="candidate")


class ApplicationRecord(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id", name="uq_applications_connection_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_status: Mapped[str] = mapped_column(String(32), default="present")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    candidate: Mapped[CandidateRecord] = relationship(back_populates="applications")
    job: Mapped[JobRecord] = relationship(back_populates="applications")


class EventRecord(Base):
    __tablename__ = "recruiting_events"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id", name="uq_events_connection_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidates.id"), nullable=True, index=True
    )
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_status: Mapped[str] = mapped_column(String(32), default="present")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    candidate: Mapped[CandidateRecord | None] = relationship(back_populates="events")


class StageRecord(Base):
    __tablename__ = "stages"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id", name="uq_stages_connection_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_status: Mapped[str] = mapped_column(String(32), default="present")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class FileMetadataRecord(Base):
    __tablename__ = "file_metadata"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id", name="uq_file_metadata_connection_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_status: Mapped[str] = mapped_column(String(32), default="present")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    candidate: Mapped[CandidateRecord] = relationship(back_populates="files")


class RawATSObjectRecord(Base):
    __tablename__ = "raw_ats_objects"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "object_type", "external_id", name="uq_raw_ats_objects_identity"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    object_type: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    raw_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))


class SyncRunRecord(Base):
    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    sync_type: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    jobs_seen: Mapped[int] = mapped_column(Integer, default=0)
    candidates_seen: Mapped[int] = mapped_column(Integer, default=0)
    applications_seen: Mapped[int] = mapped_column(Integer, default=0)
    events_seen: Mapped[int] = mapped_column(Integer, default=0)
    stages_seen: Mapped[int] = mapped_column(Integer, default=0)
    files_seen: Mapped[int] = mapped_column(Integer, default=0)
    source_objects_fetched: Mapped[int] = mapped_column(Integer, default=0)
    raw_objects_created: Mapped[int] = mapped_column(Integer, default=0)
    raw_objects_updated: Mapped[int] = mapped_column(Integer, default=0)
    raw_objects_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    canonical_records_created: Mapped[int] = mapped_column(Integer, default=0)
    canonical_records_updated: Mapped[int] = mapped_column(Integer, default=0)
    canonical_records_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    connection: Mapped[AtsConnectionRecord] = relationship(back_populates="sync_runs")
    errors: Mapped[list[SyncErrorRecord]] = relationship(back_populates="sync_run")


class SyncWatermarkRecord(Base):
    __tablename__ = "sync_watermarks"
    __table_args__ = (
        UniqueConstraint("connection_id", "sync_scope", name="uq_sync_watermarks_connection_scope"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ats_connections.id"), index=True)
    sync_scope: Mapped[str] = mapped_column(String(64), index=True)
    last_successful_watermark: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SyncErrorRecord(Base):
    __tablename__ = "sync_errors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sync_run_id: Mapped[str] = mapped_column(ForeignKey("sync_runs.id"), index=True)
    connection_id: Mapped[str | None] = mapped_column(
        ForeignKey("ats_connections.id"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), index=True)
    object_type: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_type: Mapped[str] = mapped_column(String(64))
    error_category: Mapped[str] = mapped_column(String(64), default="runtime")
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    sync_run: Mapped[SyncRunRecord] = relationship(back_populates="errors")


class AutomationRunRecord(Base):
    __tablename__ = "automation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow: Mapped[str] = mapped_column(String(128), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    target: Mapped[str] = mapped_column(String(255))
    request_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
