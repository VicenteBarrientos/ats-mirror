from datetime import UTC, datetime

from app.models.domain import Job, ProviderHealth, WritePreview
from app.models.enums import Capability, JobStatus
from app.providers.base import ATSProvider
from app.providers.dry_run import DryRunProvider
from app.providers.errors import UnsupportedCapabilityError
from app.providers.mock import MockATSProvider


class JobsOnlyProvider(ATSProvider):
    @property
    def name(self) -> str:
        return "jobs-only"

    @property
    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.READ_JOBS})

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            ok=True,
            message="limited",
            capabilities=[Capability.READ_JOBS.value],
        )

    def list_jobs(self, *, limit: int = 50, offset: int = 0) -> list[Job]:
        self.require(Capability.READ_JOBS)
        return [
            Job(
                id="job_1",
                external_id="job_1",
                title="Example",
                status=JobStatus.OPEN,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        ]

    def get_job(self, job_id: str) -> Job:
        self.require(Capability.READ_JOBS)
        return self.list_jobs()[0]


def test_unsupported_capability_message() -> None:
    provider = JobsOnlyProvider()
    try:
        provider.list_candidates()
    except UnsupportedCapabilityError as exc:
        assert exc.provider == "jobs-only"
        assert exc.capability is Capability.READ_CANDIDATES
        assert "read_candidates" in str(exc)
    else:
        raise AssertionError("expected UnsupportedCapabilityError")


def test_add_note_unsupported() -> None:
    provider = JobsOnlyProvider()
    try:
        provider.add_candidate_note("c1", "hello")
    except UnsupportedCapabilityError as exc:
        assert "add_note" in str(exc)
    else:
        raise AssertionError("expected UnsupportedCapabilityError")


def test_dry_run_blocks_writes_but_allows_reads() -> None:
    inner = MockATSProvider()
    wrapped = DryRunProvider(inner)
    jobs = wrapped.list_jobs()
    assert jobs
    preview = wrapped.add_candidate_note("cand_alex_rivera", "secret-looking note body")
    assert isinstance(preview, WritePreview)
    assert preview.dry_run is True
    assert "Would perform: add note to candidate cand_alex_rivera" in preview.message
    assert inner._notes == []
    move = wrapped.move_candidate("cand_alex_rivera", "job_backend_senior::stage_3")
    assert isinstance(move, WritePreview)
    assert inner.get_candidate("cand_alex_rivera").current_stage == "Recruiter Review"


def test_dry_run_health_flag() -> None:
    health = DryRunProvider(MockATSProvider()).health_check()
    assert health.dry_run is True
    assert health.ok is True
