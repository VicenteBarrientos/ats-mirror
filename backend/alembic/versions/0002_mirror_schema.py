"""Mirror metadata, raw ATS objects, and sync runs.

Revision ID: 0002_mirror_schema
Revises: 0001_initial
Create Date: 2026-09-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_mirror_schema"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.execute(sa.text("UPDATE jobs SET last_synced_at = synced_at WHERE last_synced_at IS NULL"))

    with op.batch_alter_table("candidates") as batch:
        batch.add_column(sa.Column("phone", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch.add_column(sa.Column("skills", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("tags", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("source", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("social_links", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("experience", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("education", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.execute(sa.text("UPDATE candidates SET last_synced_at = synced_at WHERE last_synced_at IS NULL"))

    with op.batch_alter_table("applications") as batch:
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))

    with op.batch_alter_table("recruiting_events") as batch:
        batch.add_column(sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))

    op.create_table(
        "stages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("provider", "external_id", name="uq_stages_provider_external"),
    )
    op.create_table(
        "file_metadata",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("candidate_id", sa.String(length=36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=128), nullable=True),
        sa.Column("source_ref", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("provider", "external_id", name="uq_file_metadata_provider_external"),
    )
    op.create_table(
        "raw_ats_objects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("object_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("provider", "object_type", "external_id", name="uq_raw_ats_objects_identity"),
    )
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("sync_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("jobs_seen", sa.Integer(), nullable=False),
        sa.Column("candidates_seen", sa.Integer(), nullable=False),
        sa.Column("applications_seen", sa.Integer(), nullable=False),
        sa.Column("events_seen", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )
    op.create_table(
        "sync_errors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sync_run_id", sa.String(length=36), sa.ForeignKey("sync_runs.id"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("object_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("error_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sync_errors")
    op.drop_table("sync_runs")
    op.drop_table("raw_ats_objects")
    op.drop_table("file_metadata")
    op.drop_table("stages")
    with op.batch_alter_table("recruiting_events") as batch:
        batch.drop_column("content_hash")
        batch.drop_column("last_synced_at")
        batch.drop_column("source_updated_at")
    with op.batch_alter_table("applications") as batch:
        batch.drop_column("content_hash")
        batch.drop_column("last_synced_at")
        batch.drop_column("source_updated_at")
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
    with op.batch_alter_table("candidates") as batch:
        batch.drop_column("content_hash")
        batch.drop_column("last_synced_at")
        batch.drop_column("source_updated_at")
        batch.drop_column("updated_at")
        batch.drop_column("education")
        batch.drop_column("experience")
        batch.drop_column("social_links")
        batch.drop_column("source")
        batch.drop_column("tags")
        batch.drop_column("skills")
        batch.drop_column("summary")
        batch.drop_column("phone")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("content_hash")
        batch.drop_column("last_synced_at")
        batch.drop_column("source_updated_at")
        batch.drop_column("updated_at")
