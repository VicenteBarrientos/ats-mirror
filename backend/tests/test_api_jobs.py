from fastapi.testclient import TestClient


def test_list_jobs_empty_before_sync(client: TestClient) -> None:
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert response.json() == []


def test_list_jobs(synced_client: TestClient) -> None:
    response = synced_client.get("/api/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 3
    first = jobs[0]
    assert "title" in first
    assert "external_id" in first
    assert "workable" not in first
    # Internal id is a UUID after persistence, distinct from provider id.
    assert first["id"] != first["external_id"] or len(first["id"]) == 36


def test_get_job_by_external_and_internal_id(synced_client: TestClient) -> None:
    listed = synced_client.get("/api/jobs").json()
    job = next(item for item in listed if item["external_id"] == "job_backend_senior")
    by_external = synced_client.get("/api/jobs/job_backend_senior")
    by_internal = synced_client.get(f"/api/jobs/{job['id']}")
    assert by_external.status_code == 200
    assert by_internal.status_code == 200
    assert by_external.json()["title"] == "Senior Backend Engineer"
    assert by_internal.json()["id"] == job["id"]


def test_unknown_job_404(client: TestClient) -> None:
    response = client.get("/api/jobs/no-such-job")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
