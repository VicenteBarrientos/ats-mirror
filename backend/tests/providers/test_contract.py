import pytest
from app.models.domain import Candidate, Job
from app.models.enums import Capability
from app.providers.errors import EntityNotFoundError, UnsupportedCapabilityError

from tests.providers.helpers import contract_providers


@pytest.mark.parametrize("provider", contract_providers(), ids=lambda provider: provider.name)
def test_provider_has_stable_name(provider: object) -> None:
    assert provider.name
    assert " " not in provider.name


@pytest.mark.parametrize("provider", contract_providers(), ids=lambda provider: provider.name)
def test_health_check_does_not_leak_secrets(provider: object) -> None:
    health = provider.health_check()
    blob = health.model_dump_json().lower()
    assert "token" not in blob
    assert "bearer" not in blob
    assert health.provider == provider.name
    assert health.ok is True


@pytest.mark.parametrize("provider", contract_providers(), ids=lambda provider: provider.name)
def test_declared_read_jobs_returns_normalized_models(provider: object) -> None:
    if Capability.READ_JOBS not in provider.capabilities:
        pytest.skip("provider does not declare READ_JOBS")
    jobs = provider.list_jobs()
    assert all(isinstance(job, Job) for job in jobs)
    for job in jobs:
        assert job.id
        assert job.external_id
        assert job.title
        fetched = provider.get_job(job.external_id)
        assert fetched.external_id == job.external_id


@pytest.mark.parametrize("provider", contract_providers(), ids=lambda provider: provider.name)
def test_declared_read_candidates_returns_normalized_models(provider: object) -> None:
    if Capability.READ_CANDIDATES not in provider.capabilities:
        pytest.skip("provider does not declare READ_CANDIDATES")
    candidates = provider.list_candidates()
    assert all(isinstance(candidate, Candidate) for candidate in candidates)
    for candidate in candidates:
        assert candidate.id
        assert candidate.name
        fetched = provider.get_candidate(candidate.external_id)
        assert fetched.external_id == candidate.external_id
        applications = provider.get_candidate_applications(candidate.external_id)
        assert isinstance(applications, list)


@pytest.mark.parametrize("provider", contract_providers(), ids=lambda provider: provider.name)
def test_missing_job_raises_not_found(provider: object) -> None:
    if Capability.READ_JOBS not in provider.capabilities:
        pytest.skip("provider does not declare READ_JOBS")
    with pytest.raises(EntityNotFoundError):
        provider.get_job("does-not-exist")


@pytest.mark.parametrize("provider", contract_providers(), ids=lambda provider: provider.name)
def test_missing_candidate_raises_not_found(provider: object) -> None:
    if Capability.READ_CANDIDATES not in provider.capabilities:
        pytest.skip("provider does not declare READ_CANDIDATES")
    with pytest.raises(EntityNotFoundError):
        provider.get_candidate("does-not-exist")


@pytest.mark.parametrize("provider", contract_providers(), ids=lambda provider: provider.name)
def test_undeclared_capabilities_fail_gracefully(provider: object) -> None:
    undeclared = [cap for cap in Capability if cap not in provider.capabilities]
    if not undeclared:
        pytest.skip("provider declares every capability")
    capability = undeclared[0]
    method_name = {
        Capability.READ_JOBS: "list_jobs",
        Capability.READ_CANDIDATES: "list_candidates",
        Capability.READ_STAGES: lambda: provider.get_stages("job"),
        Capability.MOVE_CANDIDATE: lambda: provider.move_candidate("c", "s"),
        Capability.ADD_NOTE: lambda: provider.add_candidate_note("c", "note"),
        Capability.READ_FEEDBACK: lambda: provider.get_interview_feedback("c"),
        Capability.SEARCH_CANDIDATES: lambda: provider.search_candidates("x"),
        Capability.READ_EVENTS: lambda: provider.get_candidate_events("c"),
        Capability.READ_MEMBERS: "get_members",
        Capability.READ_FILES_METADATA: lambda: provider.list_candidate_files("c"),
        Capability.WEBHOOKS: None,
    }[capability]
    if method_name is None:
        pytest.skip("capability has no provider method")
    with pytest.raises(UnsupportedCapabilityError):
        if callable(method_name):
            method_name()
        elif method_name == "list_jobs":
            provider.list_jobs()
        elif method_name == "list_candidates":
            provider.list_candidates()
        else:
            getattr(provider, method_name)()
