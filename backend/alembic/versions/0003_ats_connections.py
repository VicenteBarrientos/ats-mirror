"""ATS connections and connection-scoped source identity.

Revision ID: 0003_ats_connections
Revises: 0002_mirror_schema
Create Date: 2026-09-12
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0003_ats_connections"
down_revision: Union[str, Sequence[str], None] = "0002_mirror_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MIRROR_TABLES = (
    "jobs",
    "candidates",
    "applications",
    "recruiting_events",
    "stages",
    "file_metadata",
    "raw_ats_objects",
    "sync_runs",
    "sync_errors",
)

_OLD_UNIQUES = {
    "jobs": "uq_jobs_provider_external",
    "candidates": "uq_candidates_provider_external",
    "applications": "uq_applications_provider_external",
    "recruiting_events": "uq_events_provider_external",
    "stages": "uq_stages_provider_external",
    "file_metadata": "uq_file_metadata_provider_external",
}

_NEW_UNIQUES = {
    "jobs": ("uq_jobs_connection_external", ("connection_id", "external_id")),
    "candidates": ("uq_candidates_connection_external", ("connection_id", "external_id")),
    "applications": ("uq_applications_connection_external", ("connection_id", "external_id")),
    "recruiting_events": ("uq_events_connection_external", ("connection_id", "external_id")),
    "stages": ("uq_stages_connection_external", ("connection_id", "external_id")),
    "file_metadata": ("uq_file_metadata_connection_external", ("connection_id", "external_id")),
    "raw_ats_objects": (
        "uq_raw_ats_objects_identity",
        ("connection_id", "object_type", "external_id"),
    ),
}


def upgrade() -> None:
    op.create_table(
        "ats_connections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("external_account_id", sa.String(length=255), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "external_account_id", name="uq_ats_connections_provider_account"),
    )

    for table in _MIRROR_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("connection_id", sa.String(length=36), nullable=True))
            if table not in {"sync_runs", "sync_errors", "raw_ats_objects"}:
                batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
                if table != "raw_ats_objects":
                    batch.add_column(
                        sa.Column("source_status", sa.String(length=32), nullable=True)
                    )
            if table == "raw_ats_objects":
                batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("sync_runs") as batch:
        batch.add_column(sa.Column("stages_seen", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("files_seen", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source_objects_fetched", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("raw_objects_created", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("raw_objects_updated", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("raw_objects_unchanged", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("canonical_records_created", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("canonical_records_updated", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("canonical_records_unchanged", sa.Integer(), nullable=True))

    with op.batch_alter_table("sync_errors") as batch:
        batch.add_column(sa.Column("error_category", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("http_status", sa.Integer(), nullable=True))

    conn = op.get_bind()
    providers: set[str] = set()
    for table in _MIRROR_TABLES:
        rows = conn.execute(sa.text(f"SELECT DISTINCT provider FROM {table}")).fetchall()
        providers.update(str(row[0]) for row in rows if row[0])
    provider_ids: dict[str, str] = {}
    for provider in sorted(providers):
        connection_id = str(uuid4())
        account_id = "local" if provider == "mock" else "default"
        account_name = "Mock ATS" if provider == "mock" else provider
        conn.execute(
            sa.text(
                "INSERT INTO ats_connections "
                "(id, provider, external_account_id, account_name, created_at, updated_at) "
                "VALUES (:id, :provider, :account_id, :account_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": connection_id,
                "provider": provider,
                "account_id": account_id,
                "account_name": account_name,
            },
        )
        provider_ids[provider] = connection_id
    for table in _MIRROR_TABLES:
        for provider, connection_id in provider_ids.items():
            conn.execute(
                sa.text(
                    f"UPDATE {table} SET connection_id = :cid WHERE provider = :provider"
                ),
                {"cid": connection_id, "provider": provider},
            )
        if table not in {"sync_runs", "sync_errors", "raw_ats_objects"}:
            conn.execute(sa.text(f"UPDATE {table} SET source_status = 'present'"))
        if table == "sync_runs":
            conn.execute(
                sa.text(
                    "UPDATE sync_runs SET stages_seen = COALESCE(stages_seen, 0), "
                    "files_seen = COALESCE(files_seen, 0), "
                    "source_objects_fetched = COALESCE(source_objects_fetched, "
                    "jobs_seen + candidates_seen + applications_seen + events_seen), "
                    "raw_objects_created = COALESCE(raw_objects_created, 0), "
                    "raw_objects_updated = COALESCE(raw_objects_updated, 0), "
                    "raw_objects_unchanged = COALESCE(raw_objects_unchanged, 0), "
                    "canonical_records_created = COALESCE(canonical_records_created, created_count), "
                    "canonical_records_updated = COALESCE(canonical_records_updated, updated_count), "
                    "canonical_records_unchanged = COALESCE(canonical_records_unchanged, unchanged_count)"
                )
            )
        if table == "sync_errors":
            conn.execute(
                sa.text(
                    "UPDATE sync_errors SET error_category = COALESCE(error_category, 'runtime')"
                )
            )

    for table, old_name in _OLD_UNIQUES.items():
        new_name, cols = _NEW_UNIQUES[table]
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(old_name, type_="unique")
            batch.create_unique_constraint(new_name, list(cols))
            batch.create_foreign_key(
                f"fk_{table}_connection_id",
                "ats_connections",
                ["connection_id"],
                ["id"],
            )

    with op.batch_alter_table("raw_ats_objects") as batch:
        batch.drop_constraint("uq_raw_ats_objects_identity", type_="unique")
        batch.create_unique_constraint(
            "uq_raw_ats_objects_identity",
            ["connection_id", "object_type", "external_id"],
        )
        batch.create_foreign_key(
            "fk_raw_ats_objects_connection_id",
            "ats_connections",
            ["connection_id"],
            ["id"],
        )

    for table in ("sync_runs", "sync_errors"):
        with op.batch_alter_table(table) as batch:
            batch.create_foreign_key(
                f"fk_{table}_connection_id",
                "ats_connections",
                ["connection_id"],
                ["id"],
            )


def downgrade() -> None:
    raise RuntimeError("0003_ats_connections cannot be reversed without data loss.")
