from datetime import UTC, datetime

from app.models.orm import CandidateRecord, JobRecord, RawATSObjectRecord
from app.providers.mock import MockATSProvider
from app.sync.service import SyncService
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


def test_full_mock_sync_then_idempotent_repeat(client, sqlite_url: str) -> None:
    first = client.post("/api/sync")
    assert first.status_code == 200
    payload = first.json()
    assert payload["status"] == "completed"
    assert payload["error_count"] == 0
    assert payload["jobs_seen"] >= 3
    assert payload["candidates_seen"] >= 3
    assert payload["applications_seen"] >= 3
    assert payload["events_seen"] >= 1
    assert payload["created_count"] > 0
    assert payload["canonical_records_created"] == payload["created_count"]
    assert payload["stages_seen"] >= 1
    assert payload["source_objects_fetched"] == (
        payload["jobs_seen"]
        + payload["candidates_seen"]
        + payload["applications_seen"]
        + payload["events_seen"]
        + payload["stages_seen"]
        + payload["files_seen"]
    )

    engine = create_engine(sqlite_url)
    with Session(engine) as session:
        jobs = session.scalars(select(JobRecord)).all()
        candidates = session.scalars(select(CandidateRecord)).all()
        raw = session.scalars(select(RawATSObjectRecord)).all()
        assert len(jobs) == payload["jobs_seen"]
        assert len(candidates) == payload["candidates_seen"]
        assert raw
        assert {row.provider for row in jobs} == {"mock"}

    second = client.post("/api/sync")
    assert second.status_code == 200
    repeat = second.json()
    assert repeat["status"] == "completed"
    assert repeat["created_count"] == 0
    assert repeat["updated_count"] == 0
    assert repeat["unchanged_count"] > 0
    assert repeat["error_count"] == 0
    with Session(engine) as session:
        hashes = {row.content_hash for row in session.scalars(select(JobRecord)).all()}
        assert None not in hashes
        seen = [row.last_seen_at for row in session.scalars(select(JobRecord)).all()]
        assert all(item is not None for item in seen)

    listed = client.get("/api/jobs").json()
    assert [job["id"] for job in listed] == [
        job["id"] for job in client.get("/api/jobs").json()
    ]


def test_two_workable_connections_can_share_external_id(sqlite_url: str) -> None:
    from app.models.orm import AtsConnectionRecord, Base

    engine = create_engine(sqlite_url)
    Base.metadata.create_all(engine)
    now = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
    with Session(engine) as session:
        first = AtsConnectionRecord(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            provider="workable",
            external_account_id="acme",
            account_name="Acme",
            created_at=now,
            updated_at=now,
        )
        second = AtsConnectionRecord(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            provider="workable",
            external_account_id="contoso",
            account_name="Contoso",
            created_at=now,
            updated_at=now,
        )
        session.add_all(
            [
                first,
                second,
                JobRecord(
                    id="11111111-1111-1111-1111-111111111111",
                    connection_id=first.id,
                    provider="workable",
                    external_id="abc123",
                    title="Acme role",
                    status="open",
                    created_at=now,
                    synced_at=now,
                    last_synced_at=now,
                    last_seen_at=now,
                    source_status="present",
                ),
                JobRecord(
                    id="22222222-2222-2222-2222-222222222222",
                    connection_id=second.id,
                    provider="workable",
                    external_id="abc123",
                    title="Contoso role",
                    status="open",
                    created_at=now,
                    synced_at=now,
                    last_synced_at=now,
                    last_seen_at=now,
                    source_status="present",
                ),
            ]
        )
        session.commit()
        rows = session.scalars(select(JobRecord)).all()
        assert len(rows) == 2
        assert {row.connection_id for row in rows} == {first.id, second.id}


def test_incremental_detects_candidate_change_and_leaves_others(sqlite_url: str) -> None:
    from app.db.session import dispose_engine, init_engine

    engine = init_engine(sqlite_url)
    factory = sessionmaker(bind=engine)
    provider = MockATSProvider()
    try:
        with factory() as session:
            first = SyncService(session, provider).sync_all()
            session.commit()
        assert first.status.value == "completed"
        with factory() as session:
            second = SyncService(session, provider).sync_incremental()
            session.commit()
        assert second.sync_type == "incremental"
        assert second.created_count == 0
        assert second.updated_count == 0
        provider.update_candidate("cand_alex_rivera", headline="Updated sample headline")
        with factory() as session:
            third = SyncService(session, provider).sync_incremental()
            session.commit()
            changed = session.scalar(
                select(CandidateRecord).where(CandidateRecord.external_id == "cand_alex_rivera")
            )
            unchanged = session.scalar(
                select(CandidateRecord).where(CandidateRecord.external_id == "cand_jordan_hale")
            )
            assert changed is not None
            assert changed.headline == "Updated sample headline"
            assert unchanged is not None
            assert unchanged.headline != "Updated sample headline"
        assert third.updated_count >= 1
        assert third.created_count == 0
        assert third.candidates_seen == 1
    finally:
        dispose_engine()


def test_failed_sync_does_not_advance_failed_watermark(sqlite_url: str) -> None:
    from app.db.session import dispose_engine, init_engine
    from app.models.orm import SyncWatermarkRecord
    from app.providers.errors import ProviderUnavailableError
    from app.sync.watermarks import SCOPE_CANDIDATES, SCOPE_JOBS

    engine = init_engine(sqlite_url)
    factory = sessionmaker(bind=engine)

    class BoomCandidates(MockATSProvider):
        def iter_candidates(self, *, page_size: int = 50, updated_after=None):  # type: ignore[no-untyped-def]
            raise ProviderUnavailableError("candidates unavailable")

    try:
        with factory() as session:
            SyncService(session, MockATSProvider()).sync_all()
            session.commit()
            before = session.scalar(
                select(SyncWatermarkRecord).where(SyncWatermarkRecord.sync_scope == SCOPE_CANDIDATES)
            )
            assert before is not None
            previous = before.last_successful_watermark
        with factory() as session:
            result = SyncService(session, BoomCandidates()).sync_incremental()
            session.commit()
            after_jobs = session.scalar(
                select(SyncWatermarkRecord).where(SyncWatermarkRecord.sync_scope == SCOPE_JOBS)
            )
            after_candidates = session.scalar(
                select(SyncWatermarkRecord).where(SyncWatermarkRecord.sync_scope == SCOPE_CANDIDATES)
            )
        assert result.status.value in {"failed", "completed_with_errors"}
        assert after_candidates is not None
        assert after_candidates.last_successful_watermark == previous
        assert after_jobs is not None
        assert after_jobs.last_successful_watermark is not None
    finally:
        dispose_engine()


def test_full_sync_marks_missing_without_hard_delete(sqlite_url: str) -> None:
    from app.db.session import dispose_engine, init_engine

    engine = init_engine(sqlite_url)
    factory = sessionmaker(bind=engine)
    provider = MockATSProvider()
    try:
        with factory() as session:
            SyncService(session, provider).sync_all()
            session.commit()
        removed = next(iter(provider._jobs))
        del provider._jobs[removed]
        with factory() as session:
            SyncService(session, provider).sync_all()
            session.commit()
            row = session.scalar(select(JobRecord).where(JobRecord.external_id == removed))
            assert row is not None
            assert row.source_status == "missing_from_source"
            assert row.last_seen_at is not None
    finally:
        dispose_engine()


def test_incremental_does_not_mark_missing(sqlite_url: str) -> None:
    from app.db.session import dispose_engine, init_engine

    engine = init_engine(sqlite_url)
    factory = sessionmaker(bind=engine)
    provider = MockATSProvider()
    try:
        with factory() as session:
            SyncService(session, provider).sync_all()
            session.commit()
        removed = next(iter(provider._jobs))
        del provider._jobs[removed]
        with factory() as session:
            SyncService(session, provider).sync_incremental()
            session.commit()
            row = session.scalar(select(JobRecord).where(JobRecord.external_id == removed))
            assert row is not None
            assert row.source_status == "present"
    finally:
        dispose_engine()


def test_partial_candidate_failure_does_not_abort_sync(sqlite_url: str) -> None:
    from app.db.session import init_engine

    engine = init_engine(sqlite_url)
    factory = sessionmaker(bind=engine)

    class Flaky(MockATSProvider):
        def get_candidate_applications(self, candidate_id: str):  # type: ignore[no-untyped-def]
            if candidate_id == "cand_alex_rivera":
                raise RuntimeError("transient candidate failure")
            return super().get_candidate_applications(candidate_id)

    with factory() as session:
        result = SyncService(session, Flaky()).sync_all()
        session.commit()
    from app.db.session import dispose_engine

    try:
        assert result.status.value == "completed_with_errors"
        assert result.error_count >= 1
        assert result.jobs_seen >= 3
        assert result.candidates_seen >= 3
        with factory() as session:
            names = {row.external_id for row in session.scalars(select(CandidateRecord)).all()}
            assert "cand_alex_rivera" in names
            assert "cand_jordan_hale" in names
    finally:
        dispose_engine()
