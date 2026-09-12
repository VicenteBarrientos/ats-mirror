from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

from app.models.domain import (
    Application,
    Candidate,
    CandidateNote,
    FileMetadata,
    InterviewFeedback,
    Job,
    Member,
    ProviderHealth,
    RecruitingEvent,
    Stage,
)
from app.models.enums import Capability, EventType
from app.providers import mock_data
from app.providers.base import ATSProvider
from app.providers.errors import EntityNotFoundError
from app.providers.pagination import paginate


class MockATSProvider(ATSProvider):
    """Fully capable in-memory ATS. No network. Safe default for local development."""

    def __init__(self) -> None:
        data = mock_data.snapshot()
        self._jobs: dict[str, Job] = {job.external_id: job for job in data["jobs"]}
        self._candidates: dict[str, Candidate] = {
            candidate.external_id: candidate for candidate in data["candidates"]
        }
        self._applications: dict[str, Application] = {
            application.external_id: application for application in data["applications"]
        }
        self._stages: dict[str, Stage] = {stage.external_id: stage for stage in data["stages"]}
        self._events: dict[str, RecruitingEvent] = {
            event.external_id: event for event in data["events"]
        }
        self._feedback: dict[str, InterviewFeedback] = {
            item.external_id: item for item in data["feedback"]
        }
        self._members: dict[str, Member] = {member.external_id: member for member in data["members"]}
        self._notes: list[CandidateNote] = list(data["notes"])
        self._source_updated: dict[str, datetime] = {}
        self._refresh_job_counts()

    @property
    def name(self) -> str:
        return "mock"

    @property
    def account_id(self) -> str | None:
        return "local"

    @property
    def account_name(self) -> str | None:
        return "Mock ATS"

    @property
    def capabilities(self) -> frozenset[Capability]:
        return frozenset(Capability)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            ok=True,
            message="Mock ATS is ready. No external credentials required.",
            capabilities=sorted(cap.value for cap in self.capabilities),
            dry_run=False,
            account_id=self.account_id,
            account_name=self.account_name,
        )

    def list_jobs(self, *, limit: int = 50, offset: int = 0) -> list[Job]:
        self.require(Capability.READ_JOBS)
        jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
        return paginate(jobs, limit=limit, offset=offset)

    def iter_jobs(self, *, page_size: int = 50, updated_after: datetime | None = None) -> Iterator[Job]:
        del page_size
        self.require(Capability.READ_JOBS)
        jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
        for job in jobs:
            timestamp = self._source_updated.get(job.external_id, job.created_at)
            if updated_after is not None and timestamp <= updated_after:
                continue
            yield job

    def get_job(self, job_id: str) -> Job:
        self.require(Capability.READ_JOBS)
        job = self._jobs.get(job_id)
        if job is None:
            raise EntityNotFoundError("job", job_id)
        return job

    def list_candidates(
        self,
        job_id: str | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Candidate]:
        self.require(Capability.READ_CANDIDATES)
        candidates = list(self._candidates.values())
        if job_id is not None:
            if job_id not in self._jobs:
                raise EntityNotFoundError("job", job_id)
            linked = {
                application.candidate_id
                for application in self._applications.values()
                if application.job_id == job_id
            }
            candidates = [candidate for candidate in candidates if candidate.id in linked]
        candidates.sort(key=lambda candidate: candidate.created_at, reverse=True)
        return paginate(candidates, limit=limit, offset=offset)

    def iter_candidates(
        self, *, page_size: int = 50, updated_after: datetime | None = None
    ) -> Iterator[Candidate]:
        del page_size
        self.require(Capability.READ_CANDIDATES)
        candidates = sorted(self._candidates.values(), key=lambda item: item.created_at, reverse=True)
        for candidate in candidates:
            timestamp = self._source_updated.get(candidate.external_id, candidate.created_at)
            if updated_after is not None and timestamp <= updated_after:
                continue
            yield candidate

    def update_candidate(self, candidate_id: str, **fields: object) -> Candidate:
        current = self.get_candidate(candidate_id)
        updated = current.model_copy(update=fields)
        self._candidates[candidate_id] = updated
        self._source_updated[updated.external_id] = datetime.now(UTC)
        return updated

    def get_candidate(self, candidate_id: str) -> Candidate:
        self.require(Capability.READ_CANDIDATES)
        candidate = self._candidates.get(candidate_id)
        if candidate is None:
            raise EntityNotFoundError("candidate", candidate_id)
        return candidate

    def get_candidate_applications(self, candidate_id: str) -> list[Application]:
        self.require(Capability.READ_CANDIDATES)
        self.get_candidate(candidate_id)
        return [
            application
            for application in self._applications.values()
            if application.candidate_id == candidate_id
        ]

    def get_stages(self, job_id: str | None = None) -> list[Stage]:
        self.require(Capability.READ_STAGES)
        if job_id is None:
            return sorted(self._stages.values(), key=lambda stage: (stage.job_id or "", stage.position))
        self.get_job(job_id)
        stages = [stage for stage in self._stages.values() if stage.job_id == job_id]
        return sorted(stages, key=lambda stage: stage.position)

    def list_candidate_files(self, candidate_id: str) -> list[FileMetadata]:
        self.require(Capability.READ_FILES_METADATA)
        self.get_candidate(candidate_id)
        return []

    def move_candidate(self, candidate_id: str, stage_id: str) -> Candidate:
        self.require(Capability.MOVE_CANDIDATE)
        candidate = self.get_candidate(candidate_id)
        stage = self._stages.get(stage_id)
        if stage is None:
            raise EntityNotFoundError("stage", stage_id)
        previous_stage = candidate.current_stage
        updated = candidate.model_copy(update={"current_stage": stage.name})
        self._candidates[candidate_id] = updated
        for application_id, application in self._applications.items():
            if application.candidate_id == candidate_id and application.job_id == stage.job_id:
                self._applications[application_id] = application.model_copy(
                    update={"stage": stage.name}
                )
        event = RecruitingEvent(
            id=f"evt_{uuid4().hex[:12]}",
            external_id=f"evt_{uuid4().hex[:12]}",
            candidate_id=candidate_id,
            job_id=stage.job_id,
            event_type=EventType.STAGE_CHANGED,
            timestamp=datetime.now(UTC),
            metadata={"from_stage": previous_stage, "to_stage": stage.name},
        )
        self._events[event.external_id] = event
        return updated

    def add_candidate_note(self, candidate_id: str, note: str) -> CandidateNote:
        self.require(Capability.ADD_NOTE)
        self.get_candidate(candidate_id)
        created = CandidateNote(
            id=f"note_{uuid4().hex[:12]}",
            candidate_id=candidate_id,
            body=note,
            created_at=datetime.now(UTC),
            dry_run=False,
        )
        self._notes.append(created)
        return created

    def get_candidate_events(
        self, candidate_id: str, *, updated_after: datetime | None = None
    ) -> list[RecruitingEvent]:
        self.require(Capability.READ_EVENTS)
        self.get_candidate(candidate_id)
        events = [
            event for event in self._events.values() if event.candidate_id == candidate_id
        ]
        if updated_after is not None:
            events = [event for event in events if event.timestamp > updated_after]
        return sorted(events, key=lambda event: event.timestamp)

    def get_interview_feedback(self, candidate_id: str) -> list[InterviewFeedback]:
        self.require(Capability.READ_FEEDBACK)
        self.get_candidate(candidate_id)
        return [item for item in self._feedback.values() if item.candidate_id == candidate_id]

    def get_members(self) -> list[Member]:
        self.require(Capability.READ_MEMBERS)
        return list(self._members.values())

    def search_candidates(self, query: str, *, limit: int = 50) -> list[Candidate]:
        self.require(Capability.SEARCH_CANDIDATES)
        needle = query.strip().lower()
        if not needle:
            return []
        matches = [
            candidate
            for candidate in self._candidates.values()
            if needle in candidate.name.lower()
            or (candidate.headline and needle in candidate.headline.lower())
            or (candidate.email and needle in candidate.email.lower())
        ]
        return paginate(matches, limit=limit, offset=0)

    def _refresh_job_counts(self) -> None:
        counts: dict[str, int] = {}
        for application in self._applications.values():
            counts[application.job_id] = counts.get(application.job_id, 0) + 1
        for job_id, job in self._jobs.items():
            self._jobs[job_id] = job.model_copy(update={"candidate_count": counts.get(job_id, 0)})
