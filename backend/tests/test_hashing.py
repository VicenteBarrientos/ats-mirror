from datetime import UTC, datetime

from app.models.domain import Job
from app.models.enums import JobStatus
from app.sync.hashing import canonical_content_hash, raw_content_hash


def test_canonical_hash_ignores_internal_id_and_sync_metadata() -> None:
    created = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
    job = Job(
        id="11111111-1111-1111-1111-111111111111",
        external_id="GROOV005",
        title="Office Manager",
        department="Administration",
        location="Chicago, Illinois, United States",
        status=JobStatus.OPEN,
        description="Keep the office running.",
        created_at=created,
        candidate_count=3,
    )
    first = canonical_content_hash("job", job)
    second = canonical_content_hash(
        "job",
        job.model_copy(
            update={
                "id": "22222222-2222-2222-2222-222222222222",
                "candidate_count": 99,
            }
        ),
    )
    assert first == second


def test_raw_hash_ignores_last_synced_at_and_preview_url() -> None:
    payload = {
        "id": "167636b1",
        "shortcode": "GROOV005",
        "title": "Office Manager",
        "updated_at": "2015-06-07T00:00:00Z",
        "preview_url": "https://s3.example/tmp",
        "last_synced_at": "2026-09-12T18:00:00Z",
    }
    other = {
        **payload,
        "last_synced_at": "2026-09-12T19:00:00Z",
        "preview_url": "https://s3.example/other",
        "connection_id": "conn-1",
    }
    assert raw_content_hash(payload) == raw_content_hash(other)


def test_raw_hash_changes_when_source_updated_at_changes() -> None:
    base = {"shortcode": "GROOV005", "title": "Office Manager", "updated_at": "2015-06-07T00:00:00Z"}
    changed = {**base, "updated_at": "2015-06-08T00:00:00Z"}
    assert raw_content_hash(base) != raw_content_hash(changed)
