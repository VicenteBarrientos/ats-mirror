"""Initial normalized recruiting schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "external_id", name="uq_jobs_provider_external"),
    )
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("headline", sa.String(length=512), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("current_stage", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "external_id", name="uq_candidates_provider_external"),
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("candidate_id", sa.String(length=36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("stage", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("provider", "external_id", name="uq_applications_provider_external"),
    )
    op.create_table(
        "recruiting_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("candidate_id", sa.String(length=36), sa.ForeignKey("candidates.id"), nullable=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.UniqueConstraint("provider", "external_id", name="uq_events_provider_external"),
    )
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workflow", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("request_summary", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("automation_runs")
    op.drop_table("recruiting_events")
    op.drop_table("applications")
    op.drop_table("candidates")
    op.drop_table("jobs")
