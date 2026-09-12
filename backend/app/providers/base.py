from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime
from typing import Any

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
    WritePreview,
)
from app.models.enums import Capability
from app.providers.errors import UnsupportedCapabilityError
from app.providers.pagination import iter_offset_pages


class ATSProvider(ABC):
    """ATS-agnostic adapter.

    Business logic must call this interface, never a vendor SDK or HTTP client.
    Methods the provider does not support raise UnsupportedCapabilityError.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable provider key, e.g. 'mock' or 'workable'."""

    @property
    def account_id(self) -> str | None:
        """Stable account key within the provider. Used for ats_connections."""
        return None

    @property
    def account_name(self) -> str | None:
        """Human-readable account label. Must not include secrets."""
        return None

    @property
    @abstractmethod
    def capabilities(self) -> frozenset[Capability]:
        """Declared operations this adapter can perform."""

    def require(self, capability: Capability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedCapabilityError(self.name, capability)

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Connectivity / configuration check. Must not leak secrets."""

    def list_jobs(self, *, limit: int = 50, offset: int = 0) -> list[Job]:
        self.require(Capability.READ_JOBS)
        raise NotImplementedError(self._missing(Capability.READ_JOBS, "list_jobs"))

    def get_job(self, job_id: str) -> Job:
        self.require(Capability.READ_JOBS)
        raise NotImplementedError(self._missing(Capability.READ_JOBS, "get_job"))

    def list_candidates(
        self,
        job_id: str | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Candidate]:
        self.require(Capability.READ_CANDIDATES)
        raise NotImplementedError(self._missing(Capability.READ_CANDIDATES, "list_candidates"))

    def get_candidate(self, candidate_id: str) -> Candidate:
        self.require(Capability.READ_CANDIDATES)
        raise NotImplementedError(self._missing(Capability.READ_CANDIDATES, "get_candidate"))

    def get_candidate_applications(self, candidate_id: str) -> list[Application]:
        self.require(Capability.READ_CANDIDATES)
        raise NotImplementedError(
            self._missing(Capability.READ_CANDIDATES, "get_candidate_applications")
        )

    def get_stages(self, job_id: str | None = None) -> list[Stage]:
        self.require(Capability.READ_STAGES)
        raise NotImplementedError(self._missing(Capability.READ_STAGES, "get_stages"))

    def list_candidate_files(self, candidate_id: str) -> list[FileMetadata]:
        self.require(Capability.READ_FILES_METADATA)
        raise NotImplementedError(
            self._missing(Capability.READ_FILES_METADATA, "list_candidate_files")
        )

    def iter_jobs(self, *, page_size: int = 50, updated_after: datetime | None = None) -> Iterator[Job]:
        self.require(Capability.READ_JOBS)
        del updated_after
        yield from iter_offset_pages(self.list_jobs, page_size=page_size)

    def iter_candidates(
        self, *, page_size: int = 50, updated_after: datetime | None = None
    ) -> Iterator[Candidate]:
        self.require(Capability.READ_CANDIDATES)
        del updated_after
        yield from iter_offset_pages(self.list_candidates, page_size=page_size)

    def consume_raw(self, object_type: str, external_id: str) -> dict[str, Any] | None:
        """Optional source payload captured during the last provider read. Default: none."""
        return None

    def move_candidate(
        self, candidate_id: str, stage_id: str
    ) -> WritePreview | Candidate:
        self.require(Capability.MOVE_CANDIDATE)
        raise NotImplementedError(self._missing(Capability.MOVE_CANDIDATE, "move_candidate"))

    def add_candidate_note(self, candidate_id: str, note: str) -> CandidateNote | WritePreview:
        self.require(Capability.ADD_NOTE)
        raise NotImplementedError(self._missing(Capability.ADD_NOTE, "add_candidate_note"))

    def get_candidate_events(
        self, candidate_id: str, *, updated_after: datetime | None = None
    ) -> list[RecruitingEvent]:
        self.require(Capability.READ_EVENTS)
        del updated_after
        raise NotImplementedError(self._missing(Capability.READ_EVENTS, "get_candidate_events"))

    def get_interview_feedback(self, candidate_id: str) -> list[InterviewFeedback]:
        self.require(Capability.READ_FEEDBACK)
        raise NotImplementedError(
            self._missing(Capability.READ_FEEDBACK, "get_interview_feedback")
        )

    def get_members(self) -> list[Member]:
        self.require(Capability.READ_MEMBERS)
        raise NotImplementedError(self._missing(Capability.READ_MEMBERS, "get_members"))

    def search_candidates(self, query: str, *, limit: int = 50) -> list[Candidate]:
        self.require(Capability.SEARCH_CANDIDATES)
        raise NotImplementedError(
            self._missing(Capability.SEARCH_CANDIDATES, "search_candidates")
        )

    def _missing(self, capability: Capability, method: str) -> str:
        return (
            f"Provider '{self.name}' declared capability '{capability.value}' "
            f"but did not implement {method}()."
        )
