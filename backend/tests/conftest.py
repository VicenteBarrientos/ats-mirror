from collections.abc import Generator
from pathlib import Path

import pytest
from app.config import reset_settings_cache
from fastapi.testclient import TestClient


@pytest.fixture
def sqlite_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, sqlite_url: str) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("ATS_PROVIDER", "mock")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DATABASE_URL", sqlite_url)
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.setenv("WORKABLE_SUBDOMAIN", "")
    monkeypatch.setenv("WORKABLE_ACCESS_TOKEN", "")
    reset_settings_cache()
    from app.main import create_app

    application = create_app()
    with TestClient(application) as test_client:
        yield test_client
    reset_settings_cache()


@pytest.fixture
def synced_client(client: TestClient) -> TestClient:
    response = client.post("/api/sync")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    return client
