from pathlib import Path

from alembic.config import Config
from app.config import reset_settings_cache
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_creates_tables(tmp_path: Path, monkeypatch: object) -> None:
    db_path = tmp_path / "alembic.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)  # type: ignore[attr-defined]
    reset_settings_cache()
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("prepend_sys_path", str(backend_root))
    from alembic import command

    command.upgrade(config, "head")
    inspector = inspect(create_engine(url))
    tables = set(inspector.get_table_names())
    assert {
        "jobs",
        "candidates",
        "applications",
        "recruiting_events",
        "automation_runs",
        "audit_logs",
        "raw_ats_objects",
        "sync_runs",
        "sync_errors",
        "stages",
        "file_metadata",
        "ats_connections",
        "sync_watermarks",
    }.issubset(tables)
    reset_settings_cache()


def test_alembic_0003_migrates_existing_jobs(tmp_path: Path, monkeypatch: object) -> None:
    db_path = tmp_path / "legacy.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)  # type: ignore[attr-defined]
    reset_settings_cache()
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("prepend_sys_path", str(backend_root))
    from alembic import command
    from sqlalchemy import text

    command.upgrade(config, "0002_mirror_schema")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO jobs (id, provider, external_id, title, status, created_at, synced_at) "
                "VALUES ('11111111-1111-1111-1111-111111111111', 'mock', 'job_backend', "
                "'Senior Backend Engineer', 'open', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT connection_id, provider, external_id FROM jobs")
        ).one()
        assert row[0]
        assert row[1] == "mock"
        assert row[2] == "job_backend"
        connections = connection.execute(
            text("SELECT provider, external_account_id FROM ats_connections")
        ).all()
        assert ("mock", "local") in [(item[0], item[1]) for item in connections]
    reset_settings_cache()
