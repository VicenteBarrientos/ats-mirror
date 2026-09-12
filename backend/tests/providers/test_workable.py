from __future__ import annotations

from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from app.config import Settings
from app.models.enums import JobStatus
from app.providers.errors import EntityNotFoundError, ProviderConfigError, ProviderUnavailableError
from app.providers.pagination import follow_next_pages
from app.providers.workable import WorkableATSProvider
from app.providers.workable_map import map_candidate, map_job

JOB_A = {
    "id": "61884e2",
    "title": "Sales Intern",
    "shortcode": "GROOV003",
    "state": "draft",
    "department": "Sales",
    "location": {"location_str": "Portland, Oregon, United States"},
    "created_at": "2015-07-01T00:00:00Z",
    "updated_at": "2015-07-02T00:00:00Z",
    "description": "Intern on the sales team.",
}
JOB_B = {
    "id": "167636b1",
    "title": "Office Manager",
    "shortcode": "GROOV005",
    "state": "published",
    "department": "Administration",
    "location": {
        "country": "United States",
        "region": "Illinois",
        "city": "Chicago",
    },
    "created_at": "2015-06-06T00:00:00Z",
    "updated_at": "2015-06-07T00:00:00Z",
}

CANDIDATE_A = {
    "id": "ce4da98",
    "name": "Lakita Marrero",
    "headline": "Operations Manager",
    "job": {"shortcode": "GROOV005", "title": "Office Manager"},
    "stage": "Interview",
    "disqualified": True,
    "email": "lakita_marrero@gmail.com",
    "phone": "+1-555-0100",
    "domain": "twitter.com",
    "created_at": "2015-06-26T00:00:00Z",
    "updated_at": "2015-07-08T14:46:48Z",
    "skills": ["Operations", "Excel"],
    "tags": ["referral"],
    "summary": "Experienced operator.",
    "experience_entries": [{"title": "Ops Manager", "company": "Acme"}],
    "education_entries": [{"school": "State University", "degree": "BA"}],
    "social_profiles": [{"type": "linkedin", "url": "https://linkedin.com/in/lakita"}],
}


def _settings() -> Settings:
    return Settings(
        ATS_PROVIDER="workable",
        WORKABLE_SUBDOMAIN="groove-tech",
        WORKABLE_ACCESS_TOKEN="test-token",
        DRY_RUN="false",
    )


def _provider(handler: Callable[[httpx.Request], httpx.Response]) -> WorkableATSProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return WorkableATSProvider(_settings(), client=client)


def _json(request: httpx.Request, payload: dict[str, object], status: int = 200) -> httpx.Response:
    assert request.headers.get("Authorization") == "Bearer test-token"
    return httpx.Response(status, json=payload)


def test_map_job_and_candidate_from_official_examples() -> None:
    job = map_job(JOB_B)
    assert job.external_id == "GROOV005"
    assert job.status is JobStatus.OPEN
    assert job.location == "Chicago, Illinois, United States"
    candidate = map_candidate(CANDIDATE_A)
    assert candidate.external_id == "ce4da98"
    assert candidate.email == "lakita_marrero@gmail.com"
    assert "Operations" in candidate.skills


def test_workable_zero_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json(request, {"jobs": []})

    provider = _provider(handler)
    assert provider.list_jobs() == []


def test_workable_single_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = urlparse(str(request.url)).path
        if path.endswith("/jobs"):
            return _json(request, {"jobs": [JOB_B]})
        raise AssertionError(path)

    jobs = list(_provider(handler).iter_jobs())
    assert len(jobs) == 1
    assert jobs[0].title == "Office Manager"


def test_workable_multiple_pages_and_partial_last_page() -> None:
    calls = {"jobs": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        path = urlparse(url).path
        query = parse_qs(urlparse(url).query)
        if path.endswith("/jobs"):
            calls["jobs"] += 1
            if "since_id" not in query:
                return _json(
                    request,
                    {
                        "jobs": [JOB_A],
                        "paging": {
                            "next": "https://www.workable.com/spi/v3/accounts/groove-tech/jobs?limit=1&since_id=61884e2"
                        },
                    },
                )
            return _json(request, {"jobs": [JOB_B]})
        raise AssertionError(url)

    jobs = list(_provider(handler).iter_jobs(page_size=1))
    assert [job.external_id for job in jobs] == ["GROOV003", "GROOV005"]
    assert calls["jobs"] == 8


def test_workable_error_mid_pagination() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        query = parse_qs(urlparse(url).query)
        if "since_id" not in query:
            return httpx.Response(
                200,
                json={
                    "jobs": [JOB_A],
                    "paging": {
                        "next": "https://www.workable.com/spi/v3/accounts/groove-tech/jobs?limit=1&since_id=61884e2"
                    },
                },
            )
        return httpx.Response(500, json={"error": "boom"})

    with pytest.raises(ProviderUnavailableError):
        list(_provider(handler).iter_jobs(page_size=1))


def test_workable_http_unauthorized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Not authorized"})

    with pytest.raises(ProviderConfigError):
        _provider(handler).list_jobs()


def test_workable_missing_job() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not found"})

    with pytest.raises(EntityNotFoundError):
        _provider(handler).get_job("missing")


def test_workable_malformed_job_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json(request, {"jobs": [{"title": "No identity"}]})

    with pytest.raises(ValueError, match="shortcode"):
        list(_provider(handler).iter_jobs())


def test_workable_candidate_pagination_and_detail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = urlparse(str(request.url)).path
        if path.endswith("/candidates") and "ce4da98" not in path:
            return _json(request, {"candidates": [CANDIDATE_A]})
        if path.endswith("/candidates/ce4da98"):
            return _json(request, {**CANDIDATE_A, "summary": "Detailed summary"})
        if path.endswith("/stages"):
            return _json(
                request,
                {"stages": [{"slug": "applied", "name": "Applied", "kind": "applied", "position": 1}]},
            )
        if path.endswith("/activities"):
            return _json(
                request,
                {
                    "activities": [
                        {"action": "applied", "stage_name": "Applied", "created_at": "2015-06-26T00:00:00Z"}
                    ]
                },
            )
        if path.endswith("/files"):
            return _json(
                request,
                {
                    "files": [
                        {
                            "name": "resume.pdf",
                            "preview_url": "https://s3.example/tmp",
                            "source": "candidate",
                        }
                    ]
                },
            )
        if path.endswith("/jobs"):
            return _json(request, {"jobs": [JOB_B]})
        if "/accounts/" in path:
            return _json(
                request,
                {"id": "20ff5c50", "name": "Groove Tech", "subdomain": "groove-tech"},
            )
        raise AssertionError(path)

    provider = _provider(handler)
    candidates = list(provider.iter_candidates())
    assert len(candidates) == 1
    assert candidates[0].summary == "Detailed summary"
    applications = provider.get_candidate_applications("ce4da98")
    assert applications[0].job_id == "GROOV005"
    events = provider.get_candidate_events("ce4da98")
    assert events[0].event_type.value == "candidate_created"
    files = provider.list_candidate_files("ce4da98")
    assert files[0].filename == "resume.pdf"
    raw = provider.consume_raw("file", files[0].external_id)
    assert raw is not None
    assert "preview_url" not in raw
    health = provider.health_check()
    assert health.ok is True
    assert health.account_name == "Groove Tech"
    assert "token" not in health.message.lower()


def test_workable_iter_jobs_requests_every_state() -> None:
    states: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        query = parse_qs(urlparse(str(request.url)).query)
        states.extend(query.get("state", []))
        return _json(request, {"jobs": []})

    assert list(_provider(handler).iter_jobs()) == []
    assert states == ["published", "draft", "closed", "archived"]


def test_workable_jobs_and_candidates_send_updated_after() -> None:
    from datetime import UTC, datetime

    seen_jobs: list[str] = []
    seen_candidates: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        query = parse_qs(urlparse(str(request.url)).query)
        path = urlparse(str(request.url)).path
        if path.endswith("/jobs"):
            seen_jobs.extend(query.get("updated_after", []))
            return _json(request, {"jobs": []})
        if path.endswith("/candidates"):
            seen_candidates.extend(query.get("updated_after", []))
            return _json(request, {"candidates": []})
        raise AssertionError(path)

    since = datetime(2015, 7, 8, 11, 56, 16, tzinfo=UTC)
    provider = _provider(handler)
    assert list(provider.iter_jobs(updated_after=since)) == []
    assert list(provider.iter_candidates(updated_after=since)) == []
    assert seen_jobs == ["20150708T115616Z"] * 4
    assert seen_candidates == ["20150708T115616Z"]


def test_workable_health_unauthorized_does_not_leak_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Not authorized"})

    health = _provider(handler).health_check()
    assert health.ok is False
    assert "test-token" not in health.message
    assert "Bearer" not in health.message


def test_workable_rejects_non_get_in_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return _json(request, {"jobs": []})

    list(_provider(handler).iter_jobs())


def test_follow_next_pages_empty() -> None:
    def fetch(_path: str, _params: dict[str, object] | None) -> dict[str, object]:
        return {"jobs": []}

    assert list(follow_next_pages(fetch, "jobs", initial_path="/jobs")) == []


def test_workable_http_sync_is_idempotent(sqlite_url: str) -> None:
    from app.db.session import dispose_engine, init_engine
    from app.models.orm import JobRecord, RawATSObjectRecord
    from app.sync.service import SyncService
    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    methods: set[str] = set()

    def handler(request: httpx.Request) -> httpx.Response:
        methods.add(request.method)
        path = urlparse(str(request.url)).path
        if path.endswith("/jobs"):
            return _json(request, {"jobs": [JOB_B]})
        if path.endswith("/candidates") and "ce4da98" not in path:
            return _json(request, {"candidates": [CANDIDATE_A]})
        if path.endswith("/candidates/ce4da98"):
            return _json(request, CANDIDATE_A)
        if path.endswith("/stages"):
            return _json(
                request,
                {"stages": [{"slug": "applied", "name": "Applied", "kind": "applied", "position": 1}]},
            )
        if path.endswith("/activities"):
            return _json(
                request,
                {
                    "activities": [
                        {"action": "applied", "stage_name": "Applied", "created_at": "2015-06-26T00:00:00Z"}
                    ]
                },
            )
        if path.endswith("/files"):
            return _json(request, {"files": [{"name": "resume.pdf", "source": "candidate"}]})
        raise AssertionError(path)

    engine = init_engine(sqlite_url)
    factory = sessionmaker(bind=engine)
    try:
        with factory() as session:
            first = SyncService(session, _provider(handler)).sync_all()
            session.commit()
        assert first.status.value == "completed"
        assert first.jobs_seen == 1
        assert first.candidates_seen == 1
        assert first.created_count > 0
        assert first.error_count == 0
        with factory() as session:
            jobs = session.scalars(select(JobRecord)).all()
            raw = session.scalars(select(RawATSObjectRecord)).all()
            assert len(jobs) == 1
            assert jobs[0].external_id == "GROOV005"
            assert jobs[0].connection_id
            assert any(row.object_type == "job" for row in raw)
        with factory() as session:
            second = SyncService(session, _provider(handler)).sync_all()
            session.commit()
        assert second.created_count == 0
        assert second.updated_count == 0
        assert second.unchanged_count > 0
        assert methods == {"GET"}
    finally:
        dispose_engine()
