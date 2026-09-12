from fastapi.testclient import TestClient


def test_list_candidates_includes_job_and_last_event(synced_client: TestClient) -> None:
    response = synced_client.get("/api/candidates")
    assert response.status_code == 200
    alex = next(item for item in response.json() if item["external_id"] == "cand_alex_rivera")
    assert alex["job_title"] == "Senior Backend Engineer"
    assert alex["job_id"]
    assert alex["last_event_type"] in {"candidate_created", "stage_changed"}
    assert alex["last_event_at"]


def test_filter_candidates_by_job(synced_client: TestClient) -> None:
    response = synced_client.get("/api/candidates", params={"job_id": "job_backend_senior"})
    assert response.status_code == 200
    ids = {item["external_id"] for item in response.json()}
    assert "cand_alex_rivera" in ids
    assert "cand_jordan_hale" not in ids


def test_candidate_detail(synced_client: TestClient) -> None:
    response = synced_client.get("/api/candidates/cand_alex_rivera")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Alex Rivera"
    assert payload["applications"]
    assert payload["events"]
    assert payload["job_title"] == "Senior Backend Engineer"


def test_unknown_candidate_404(client: TestClient) -> None:
    response = client.get("/api/candidates/missing")
    assert response.status_code == 404
