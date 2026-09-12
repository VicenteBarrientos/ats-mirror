from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from app.models.domain import (
    Application,
    Candidate,
    FileMetadata,
    InterviewFeedback,
    Job,
    Member,
    ProviderHealth,
    RecruitingEvent,
    Stage,
    WritePreview,
)
from app.models.enums import Capability
from app.providers.base import ATSProvider

logger = logging.getLogger(__name__)


class DryRunProvider(ATSProvider):
    """Wraps any ATSProvider. Reads pass through; writes are logged, not applied."""

    def __init__(self, inner: ATSProvider) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def account_id(self) -> str | None:
        return self._inner.account_id

    @property
    def account_name(self) -> str | None:
        return self._inner.account_name

    @property
    def capabilities(self) -> frozenset[Capability]:
        return self._inner.capabilities

    @property
    def inner(self) -> ATSProvider:
        return self._inner

    def health_check(self) -> ProviderHealth:
        health = self._inner.health_check()
        return health.model_copy(update={"dry_run": True})

    def list_jobs(self, *, limit: int = 50, offset: int = 0) -> list[Job]:
        return self._inner.list_jobs(limit=limit, offset=offset)

    def get_job(self, job_id: str) -> Job:
        return self._inner.get_job(job_id)

    def list_candidates(
        self,
        job_id: str | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Candidate]:
        return self._inner.list_candidates(job_id, limit=limit, offset=offset)

    def get_candidate(self, candidate_id: str) -> Candidate:
        return self._inner.get_candidate(candidate_id)

    def get_candidate_applications(self, candidate_id: str) -> list[Application]:
        return self._inner.get_candidate_applications(candidate_id)

    def get_stages(self, job_id: str | None = None) -> list[Stage]:
        return self._inner.get_stages(job_id)

    def list_candidate_files(self, candidate_id: str) -> list[FileMetadata]:
        return self._inner.list_candidate_files(candidate_id)

    def consume_raw(self, object_type: str, external_id: str) -> dict[str, Any] | None:
        return self._inner.consume_raw(object_type, external_id)

    def iter_jobs(self, *, page_size: int = 50, updated_after: datetime | None = None) -> Iterator[Job]:
        yield from self._inner.iter_jobs(page_size=page_size, updated_after=updated_after)

    def iter_candidates(
        self, *, page_size: int = 50, updated_after: datetime | None = None
    ) -> Iterator[Candidate]:
        yield from self._inner.iter_candidates(page_size=page_size, updated_after=updated_after)

    def move_candidate(self, candidate_id: str, stage_id: str) -> WritePreview:
        self.require(Capability.MOVE_CANDIDATE)
        message = f"Would perform: move candidate {candidate_id} to stage {stage_id}"
        logger.info(message)
        return WritePreview(
            dry_run=True,
            action="move_candidate",
            target=candidate_id,
            message=message,
        )

    def add_candidate_note(self, candidate_id: str, note: str) -> WritePreview:
        self.require(Capability.ADD_NOTE)
        message = f"Would perform: add note to candidate {candidate_id}"
        logger.info(message)
        return WritePreview(
            dry_run=True,
            action="add_note",
            target=candidate_id,
            message=message,
        )

    def get_candidate_events(
        self, candidate_id: str, *, updated_after: datetime | None = None
    ) -> list[RecruitingEvent]:
        return self._inner.get_candidate_events(candidate_id, updated_after=updated_after)

    def get_interview_feedback(self, candidate_id: str) -> list[InterviewFeedback]:
        return self._inner.get_interview_feedback(candidate_id)

    def get_members(self) -> list[Member]:
        return self._inner.get_members()

    def search_candidates(self, query: str, *, limit: int = 50) -> list[Candidate]:
        return self._inner.search_candidates(query, limit=limit)
