"""Per-connection sync watermarks for incremental mirroring.

Revision ID: 0004_sync_watermarks
Revises: 0003_ats_connections
Create Date: 2026-09-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sync_watermarks"
down_revision: Union[str, Sequence[str], None] = "0003_ats_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_watermarks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("connection_id", sa.String(length=36), sa.ForeignKey("ats_connections.id"), nullable=False),
        sa.Column("sync_scope", sa.String(length=64), nullable=False),
        sa.Column("last_successful_watermark", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("connection_id", "sync_scope", name="uq_sync_watermarks_connection_scope"),
    )
    op.create_index("ix_sync_watermarks_connection_id", "sync_watermarks", ["connection_id"])
    op.create_index("ix_sync_watermarks_sync_scope", "sync_watermarks", ["sync_scope"])


def downgrade() -> None:
    op.drop_index("ix_sync_watermarks_sync_scope", table_name="sync_watermarks")
    op.drop_index("ix_sync_watermarks_connection_id", table_name="sync_watermarks")
    op.drop_table("sync_watermarks")
