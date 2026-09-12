from app.models.enums import Capability
from app.providers.mock import MockATSProvider


def test_mock_has_sample_jobs_and_candidates() -> None:
    provider = MockATSProvider()
    jobs = provider.list_jobs()
    candidates = provider.list_candidates()
    assert len(jobs) >= 3
    assert len(candidates) >= 5
    assert {job.status.value for job in jobs} >= {"open", "closed"}


def test_mock_filters_candidates_by_job() -> None:
    provider = MockATSProvider()
    backend = provider.list_candidates("job_backend_senior")
    names = {candidate.external_id for candidate in backend}
    assert "cand_alex_rivera" in names
    assert "cand_jordan_hale" not in names


def test_mock_stages_and_events() -> None:
    provider = MockATSProvider()
    stages = provider.get_stages("job_backend_senior")
    assert [stage.name for stage in stages][1] == "Recruiter Review"
    events = provider.get_candidate_events("cand_alex_rivera")
    assert events
    assert events[0].candidate_id == "cand_alex_rivera"


def test_mock_search() -> None:
    provider = MockATSProvider()
    matches = provider.search_candidates("FastAPI")
    assert any(candidate.external_id == "cand_alex_rivera" for candidate in matches)


def test_mock_write_note_and_move() -> None:
    provider = MockATSProvider()
    note = provider.add_candidate_note("cand_alex_rivera", "Prep briefing")
    assert note.dry_run is False
    assert note.candidate_id == "cand_alex_rivera"
    stages = provider.get_stages("job_backend_senior")
    interview = next(stage for stage in stages if stage.name == "Interview")
    moved = provider.move_candidate("cand_alex_rivera", interview.external_id)
    assert moved.current_stage == "Interview"
    assert Capability.ADD_NOTE in provider.capabilities
