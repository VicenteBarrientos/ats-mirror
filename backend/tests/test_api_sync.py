from fastapi.testclient import TestClient


def test_sync_status_before_and_after(client: TestClient) -> None:
    before = client.get("/api/sync/status")
    assert before.status_code == 200
    payload = before.json()
    assert payload["provider"] == "mock"
    assert payload["last_run"] is None
    assert payload["counts"]["jobs"] == 0
    assert payload["llm_api_required"] is False

    synced = client.post("/api/sync")
    assert synced.status_code == 200
    run = synced.json()
    assert run["sync_type"] == "full"

    after = client.get("/api/sync/status")
    body = after.json()
    assert body["last_run"]["id"] == run["id"]
    assert body["counts"]["jobs"] == run["jobs_seen"]
    assert body["counts"]["candidates"] == run["candidates_seen"]
    assert body["connection_state"] in {
        "connected",
        "last_sync_succeeded",
        "last_sync_failed",
        "syncing",
        "disconnected",
        "not_configured",
    }
    assert body["connection"]["provider"] == "mock"

    history = client.get("/api/sync/runs")
    assert history.status_code == 200
    assert history.json()[0]["id"] == run["id"]

    detail = client.get(f"/api/sync/runs/{run['id']}")
    assert detail.status_code == 200
    assert detail.json()["jobs_seen"] == run["jobs_seen"]


def test_dashboard_reads_come_from_sqlite(synced_client: TestClient) -> None:
    jobs = synced_client.get("/api/jobs").json()
    candidates = synced_client.get("/api/candidates").json()
    assert jobs
    assert candidates
    job = synced_client.get(f"/api/jobs/{jobs[0]['id']}").json()
    assert job["id"] == jobs[0]["id"]


def test_incremental_sync_after_full_is_near_zero(synced_client: TestClient) -> None:
    first = synced_client.post("/api/sync/incremental")
    assert first.status_code == 200
    payload = first.json()
    assert payload["sync_type"] == "incremental"
    assert payload["status"] == "completed"
    assert payload["created_count"] == 0
    assert payload["updated_count"] == 0
    assert payload["error_count"] == 0

    status = synced_client.get("/api/sync/status").json()
    assert status["last_full_sync_at"]
    assert status["last_incremental_sync_at"]
    assert status["watermarks"]["jobs"]["last_successful_watermark"]
    assert status["connections"][0]["provider"] == "mock"


def test_export_candidates_csv(synced_client: TestClient) -> None:
    response = synced_client.get("/api/export/candidates.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    body = response.text
    assert "external_candidate_id" in body
    assert "raw_payload" not in body
    assert "preview_url" not in body


def test_unknown_sync_run_404(client: TestClient) -> None:
    response = client.get("/api/sync/runs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
