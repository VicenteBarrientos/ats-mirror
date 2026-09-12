from app.models.orm import CandidateRecord, JobRecord
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def test_listing_jobs_persists_normalized_rows(synced_client: TestClient, sqlite_url: str) -> None:
    first = synced_client.get("/api/jobs").json()
    second = synced_client.get("/api/jobs").json()
    assert [job["id"] for job in first] == [job["id"] for job in second]

    engine = create_engine(sqlite_url)
    with Session(engine) as session:
        rows = session.scalars(select(JobRecord)).all()
        assert len(rows) == len(first)
        assert {row.external_id for row in rows} == {job["external_id"] for job in first}


def test_listing_candidates_persists_rows(synced_client: TestClient, sqlite_url: str) -> None:
    payload = synced_client.get("/api/candidates").json()
    engine = create_engine(sqlite_url)
    with Session(engine) as session:
        rows = session.scalars(select(CandidateRecord)).all()
        assert len(rows) == len(payload)
        alex = next(row for row in rows if row.external_id == "cand_alex_rivera")
        assert alex.name == "Alex Rivera"
        assert alex.email == "alex.rivera@example.com"
