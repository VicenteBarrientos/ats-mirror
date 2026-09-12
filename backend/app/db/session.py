from collections.abc import Generator
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.orm import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _sqlite_connect_args(url: str) -> dict[str, bool]:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def init_engine(database_url: str) -> Engine:
    global _engine, _SessionLocal
    kwargs: dict[str, object] = {"future": True}
    connect_args = _sqlite_connect_args(database_url)
    if connect_args:
        kwargs["connect_args"] = connect_args
    if database_url in {"sqlite://", "sqlite:///:memory:"}:
        kwargs["poolclass"] = StaticPool
    engine = create_engine(database_url, **kwargs)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _engine = engine
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    _ensure_legacy_columns(engine)
    _ensure_connection_identity(engine)
    return engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized.")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        raise RuntimeError("Database session factory is not initialized.")
    return _SessionLocal


def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    yield from session_scope()


def dispose_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


_LEGACY_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "jobs": [
        ("updated_at", "DATETIME"),
        ("source_updated_at", "DATETIME"),
        ("last_synced_at", "DATETIME"),
        ("last_seen_at", "DATETIME"),
        ("source_status", "VARCHAR(32)"),
        ("content_hash", "VARCHAR(64)"),
        ("connection_id", "VARCHAR(36)"),
    ],
    "candidates": [
        ("phone", "VARCHAR(255)"),
        ("summary", "TEXT"),
        ("skills", "JSON"),
        ("tags", "JSON"),
        ("source", "VARCHAR(255)"),
        ("social_links", "JSON"),
        ("experience", "JSON"),
        ("education", "JSON"),
        ("updated_at", "DATETIME"),
        ("source_updated_at", "DATETIME"),
        ("last_synced_at", "DATETIME"),
        ("last_seen_at", "DATETIME"),
        ("source_status", "VARCHAR(32)"),
        ("content_hash", "VARCHAR(64)"),
        ("connection_id", "VARCHAR(36)"),
    ],
    "applications": [
        ("created_at", "DATETIME"),
        ("updated_at", "DATETIME"),
        ("source_updated_at", "DATETIME"),
        ("last_synced_at", "DATETIME"),
        ("last_seen_at", "DATETIME"),
        ("source_status", "VARCHAR(32)"),
        ("content_hash", "VARCHAR(64)"),
        ("connection_id", "VARCHAR(36)"),
    ],
    "recruiting_events": [
        ("source_updated_at", "DATETIME"),
        ("last_synced_at", "DATETIME"),
        ("last_seen_at", "DATETIME"),
        ("source_status", "VARCHAR(32)"),
        ("content_hash", "VARCHAR(64)"),
        ("connection_id", "VARCHAR(36)"),
    ],
    "stages": [
        ("last_seen_at", "DATETIME"),
        ("source_status", "VARCHAR(32)"),
        ("connection_id", "VARCHAR(36)"),
    ],
    "file_metadata": [
        ("last_seen_at", "DATETIME"),
        ("source_status", "VARCHAR(32)"),
        ("connection_id", "VARCHAR(36)"),
    ],
    "raw_ats_objects": [
        ("last_seen_at", "DATETIME"),
        ("connection_id", "VARCHAR(36)"),
    ],
    "sync_runs": [
        ("connection_id", "VARCHAR(36)"),
        ("stages_seen", "INTEGER"),
        ("files_seen", "INTEGER"),
        ("source_objects_fetched", "INTEGER"),
        ("raw_objects_created", "INTEGER"),
        ("raw_objects_updated", "INTEGER"),
        ("raw_objects_unchanged", "INTEGER"),
        ("canonical_records_created", "INTEGER"),
        ("canonical_records_updated", "INTEGER"),
        ("canonical_records_unchanged", "INTEGER"),
    ],
    "sync_errors": [
        ("connection_id", "VARCHAR(36)"),
        ("error_category", "VARCHAR(64)"),
        ("http_status", "INTEGER"),
    ],
}

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


def _ensure_legacy_columns(engine: Engine) -> None:
    """Add columns introduced after Milestone 2 when create_all cannot ALTER existing tables."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table, columns in _LEGACY_COLUMNS.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl_type in columns:
                if name in existing:
                    continue
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))
        if "jobs" in tables:
            connection.execute(
                text("UPDATE jobs SET last_synced_at = synced_at WHERE last_synced_at IS NULL")
            )
        if "candidates" in tables:
            connection.execute(
                text("UPDATE candidates SET last_synced_at = synced_at WHERE last_synced_at IS NULL")
            )


def _ensure_connection_identity(engine: Engine) -> None:
    """Backfill ats_connections + connection_id on databases created before 0003."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "ats_connections" not in tables:
        return
    with engine.begin() as connection:
        providers: set[str] = set()
        for table in _MIRROR_TABLES:
            if table not in tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "provider" not in columns:
                continue
            rows = connection.execute(
                text(f"SELECT DISTINCT provider FROM {table} WHERE provider IS NOT NULL")
            ).fetchall()
            providers.update(str(row[0]) for row in rows if row[0])
        existing = {
            (row[0], row[1]): row[2]
            for row in connection.execute(
                text("SELECT provider, external_account_id, id FROM ats_connections")
            ).fetchall()
        }
        now = "datetime('now')"
        for provider in sorted(providers):
            account_id = "local" if provider == "mock" else "default"
            if (provider, account_id) in existing:
                continue
            connection_id = str(uuid4())
            connection.execute(
                text(
                    "INSERT INTO ats_connections "
                    "(id, provider, external_account_id, account_name, created_at, updated_at) "
                    f"VALUES (:id, :provider, :account_id, :account_name, {now}, {now})"
                ),
                {
                    "id": connection_id,
                    "provider": provider,
                    "account_id": account_id,
                    "account_name": "Mock ATS" if provider == "mock" else provider,
                },
            )
            existing[(provider, account_id)] = connection_id
        mapping = connection.execute(
            text("SELECT provider, id FROM ats_connections")
        ).fetchall()
        provider_to_id = {str(row[0]): str(row[1]) for row in mapping}
        for table in _MIRROR_TABLES:
            if table not in tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "connection_id" not in columns or "provider" not in columns:
                continue
            for provider, connection_id in provider_to_id.items():
                connection.execute(
                    text(
                        f"UPDATE {table} SET connection_id = :cid "
                        "WHERE connection_id IS NULL AND provider = :provider"
                    ),
                    {"cid": connection_id, "provider": provider},
                )
            if "source_status" in columns:
                connection.execute(
                    text(
                        f"UPDATE {table} SET source_status = 'present' "
                        "WHERE source_status IS NULL"
                    )
                )
            if "error_category" in columns:
                connection.execute(
                    text(
                        f"UPDATE {table} SET error_category = 'runtime' "
                        "WHERE error_category IS NULL"
                    )
                )
        if "sync_runs" in tables:
            connection.execute(
                text(
                    "UPDATE sync_runs SET "
                    "stages_seen = COALESCE(stages_seen, 0), "
                    "files_seen = COALESCE(files_seen, 0), "
                    "source_objects_fetched = COALESCE(source_objects_fetched, "
                    "COALESCE(jobs_seen, 0) + COALESCE(candidates_seen, 0) + "
                    "COALESCE(applications_seen, 0) + COALESCE(events_seen, 0)), "
                    "raw_objects_created = COALESCE(raw_objects_created, 0), "
                    "raw_objects_updated = COALESCE(raw_objects_updated, 0), "
                    "raw_objects_unchanged = COALESCE(raw_objects_unchanged, 0), "
                    "canonical_records_created = COALESCE(canonical_records_created, created_count), "
                    "canonical_records_updated = COALESCE(canonical_records_updated, updated_count), "
                    "canonical_records_unchanged = COALESCE(canonical_records_unchanged, unchanged_count)"
                )
            )

