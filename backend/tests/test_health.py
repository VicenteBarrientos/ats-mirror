from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["provider"] == "mock"
    assert payload["database"] == "ok"
    assert payload["dry_run"] is True
    assert payload["ai_enabled"] is False
    assert "token" not in response.text.lower()
    assert "workable_access" not in response.text.lower()


def test_provider_status(client: TestClient) -> None:
    response = client.get("/api/provider/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["ok"] is True
    assert payload["configured"] is True
    assert "read_jobs" in payload["capabilities"]
