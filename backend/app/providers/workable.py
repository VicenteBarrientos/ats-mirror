from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings
from app.models.domain import (
    Application,
    Candidate,
    FileMetadata,
    Job,
    ProviderHealth,
    RecruitingEvent,
    Stage,
)
from app.models.enums import Capability
from app.providers.base import ATSProvider
from app.providers.errors import EntityNotFoundError, ProviderConfigError, ProviderUnavailableError
from app.providers.pagination import follow_next_pages, paginate
from app.providers.workable_map import (
    map_activity,
    map_application,
    map_candidate,
    map_file,
    map_job,
    map_stage,
    sanitize_file_payload,
)
from app.sync.watermarks import format_spi_timestamp

logger = logging.getLogger(__name__)

_READ_CAPABILITIES = frozenset(
    {
        Capability.READ_JOBS,
        Capability.READ_CANDIDATES,
        Capability.READ_STAGES,
        Capability.READ_EVENTS,
        Capability.READ_FILES_METADATA,
    }
)
_JOB_STATES = ("published", "draft", "closed", "archived")


class WorkableATSProvider(ATSProvider):
    """Read-only Workable Recruiter API adapter. Official SPI v3, Bearer token."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        if not settings.workable_subdomain or not settings.workable_access_token:
            raise ProviderConfigError(
                "Workable requires WORKABLE_SUBDOMAIN and WORKABLE_ACCESS_TOKEN. "
                "Create an account API token with scopes r_jobs and r_candidates."
            )
        self._subdomain = settings.workable_subdomain.strip()
        self._timeout = settings.ats_request_timeout_seconds
        self._retries = settings.ats_max_retries
        self._base_url = f"https://{self._subdomain}.workable.com/spi/v3"
        self._owns_client = client is None
        headers = {
            "Authorization": f"Bearer {settings.workable_access_token}",
            "Accept": "application/json",
        }
        self._client = client or httpx.Client(timeout=self._timeout, headers=headers)
        if client is not None:
            self._client.headers.update(headers)
        self._raw: dict[tuple[str, str], dict[str, Any]] = {}
        self._applications: dict[str, list[Application]] = {}
        self._candidate_jobs: dict[str, str] = {}
        self._account_name = self._subdomain
        self._reported_subdomain = self._subdomain
        self._rate_remaining: int | None = None
        self._rate_reset_at: float | None = None

    @property
    def name(self) -> str:
        return "workable"

    @property
    def account_id(self) -> str | None:
        return self._subdomain

    @property
    def account_name(self) -> str | None:
        return self._account_name

    @property
    def capabilities(self) -> frozenset[Capability]:
        return _READ_CAPABILITIES

    def health_check(self) -> ProviderHealth:
        try:
            self._resolve_account()
        except ProviderConfigError as exc:
            return ProviderHealth(
                provider=self.name,
                ok=False,
                message=str(exc),
                capabilities=sorted(cap.value for cap in self.capabilities),
            )
        except ProviderUnavailableError as exc:
            return ProviderHealth(
                provider=self.name,
                ok=False,
                message=str(exc),
                capabilities=sorted(cap.value for cap in self.capabilities),
            )
        return ProviderHealth(
            provider=self.name,
            ok=True,
            message="Workable Recruiter API reachable. Read-only mirror; no ATS writes.",
            capabilities=sorted(cap.value for cap in self.capabilities),
            account_id=self.account_id,
            account_name=self.account_name,
        )

    def list_jobs(self, *, limit: int = 50, offset: int = 0) -> list[Job]:
        self.require(Capability.READ_JOBS)
        return paginate(list(self.iter_jobs()), limit=limit, offset=offset)

    def iter_jobs(self, *, page_size: int = 50, updated_after: datetime | None = None) -> Iterator[Job]:
        self.require(Capability.READ_JOBS)
        limit = min(max(page_size, 1), 100)
        seen: set[str] = set()
        for state in _JOB_STATES:
            params: dict[str, Any] = {
                "limit": limit,
                "include_fields": "description",
                "state": state,
            }
            if updated_after is not None:
                params["updated_after"] = format_spi_timestamp(updated_after)
            for payload in follow_next_pages(
                self._get,
                "jobs",
                initial_path="/jobs",
                initial_params=params,
            ):
                if not isinstance(payload, dict):
                    raise ValueError("Workable job page contained a non-object item")
                job = map_job(payload)
                if job.external_id in seen:
                    continue
                seen.add(job.external_id)
                self._remember("job", job.external_id, payload)
                yield job

    def get_job(self, job_id: str) -> Job:
        self.require(Capability.READ_JOBS)
        try:
            payload = self._get(f"/jobs/{job_id}")
        except EntityNotFoundError as exc:
            raise EntityNotFoundError("job", job_id) from exc
        body = payload.get("job") if isinstance(payload.get("job"), dict) else payload
        if not isinstance(body, dict):
            raise ValueError("Workable job detail was not an object")
        job = map_job(body)
        self._remember("job", job.external_id, body)
        return job

    def list_candidates(
        self,
        job_id: str | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Candidate]:
        self.require(Capability.READ_CANDIDATES)
        collected = list(self._iter_candidate_payloads(job_id))
        unique: list[Candidate] = []
        seen: set[str] = set()
        for payload in collected:
            candidate = map_candidate(payload)
            if candidate.external_id in seen:
                continue
            seen.add(candidate.external_id)
            unique.append(candidate)
        return paginate(unique, limit=limit, offset=offset)

    def iter_candidates(
        self, *, page_size: int = 50, updated_after: datetime | None = None
    ) -> Iterator[Candidate]:
        self.require(Capability.READ_CANDIDATES)
        seen: set[str] = set()
        for payload in self._iter_candidate_payloads(
            None, page_size=page_size, updated_after=updated_after
        ):
            candidate = map_candidate(payload)
            if candidate.external_id in seen:
                continue
            seen.add(candidate.external_id)
            yield candidate

    def get_candidate(self, candidate_id: str) -> Candidate:
        self.require(Capability.READ_CANDIDATES)
        payload = self._candidate_detail(candidate_id)
        candidate = map_candidate(payload)
        self._remember("candidate", candidate.external_id, payload)
        self._index_application(payload)
        return candidate

    def get_candidate_applications(self, candidate_id: str) -> list[Application]:
        self.require(Capability.READ_CANDIDATES)
        cached = self._applications.get(candidate_id)
        if cached is not None:
            return cached
        payload = self._candidate_detail(candidate_id)
        self._index_application(payload)
        return list(self._applications.get(candidate_id, []))

    def get_stages(self, job_id: str | None = None) -> list[Stage]:
        self.require(Capability.READ_STAGES)
        if job_id is None:
            payload = self._get("/stages")
            raw_items = payload.get("stages")
            items = raw_items if isinstance(raw_items, list) else []
            stages: list[Stage] = []
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("Workable stages contained a non-object item")
                stage = map_stage(item)
                self._remember("stage", stage.external_id, item)
                stages.append(stage)
            return stages
        payload = self._get(f"/jobs/{job_id}/stages")
        raw_items = payload.get("stages")
        items = raw_items if isinstance(raw_items, list) else []
        stages = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Workable job stages contained a non-object item")
            stage = map_stage(item, job_id=job_id)
            self._remember("stage", stage.external_id, item)
            stages.append(stage)
        return stages

    def get_candidate_events(
        self, candidate_id: str, *, updated_after: datetime | None = None
    ) -> list[RecruitingEvent]:
        self.require(Capability.READ_EVENTS)
        events: list[RecruitingEvent] = []
        job_id = self._candidate_jobs.get(candidate_id)
        params: dict[str, Any] = {"limit": 100}
        if updated_after is not None:
            params["updated_after"] = format_spi_timestamp(updated_after)
        for payload in follow_next_pages(
            self._get,
            "activities",
            initial_path=f"/candidates/{candidate_id}/activities",
            initial_params=params,
        ):
            if not isinstance(payload, dict):
                raise ValueError("Workable activity page contained a non-object item")
            event = map_activity(payload, candidate_id=candidate_id, job_id=job_id)
            raw = dict(payload)
            raw.pop("body", None)
            self._remember("event", event.external_id, raw)
            events.append(event)
        return events

    def list_candidate_files(self, candidate_id: str) -> list[FileMetadata]:
        self.require(Capability.READ_FILES_METADATA)
        payload = self._get(f"/candidates/{candidate_id}/files")
        raw_files = payload.get("files")
        items = raw_files if isinstance(raw_files, list) else []
        files: list[FileMetadata] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Workable files contained a non-object item")
            file_meta = map_file(item, candidate_id=candidate_id)
            self._remember("file", file_meta.external_id, sanitize_file_payload(item))
            files.append(file_meta)
        return files

    def consume_raw(self, object_type: str, external_id: str) -> dict[str, Any] | None:
        return self._raw.pop((object_type, external_id), None)

    def _resolve_account(self) -> None:
        """Smallest official read that verifies token, subdomain, and account name."""
        try:
            payload = self._get(f"/accounts/{self._subdomain}")
        except EntityNotFoundError:
            self._get("/jobs", {"limit": 1})
            return
        account = payload.get("account") if isinstance(payload.get("account"), dict) else payload
        if not isinstance(account, dict):
            self._get("/jobs", {"limit": 1})
            return
        name = account.get("name")
        subdomain = account.get("subdomain")
        if isinstance(name, str) and name.strip():
            self._account_name = name.strip()
        if isinstance(subdomain, str) and subdomain.strip():
            self._reported_subdomain = subdomain.strip()

    def _iter_candidate_payloads(
        self, job_id: str | None, *, page_size: int = 50, updated_after: datetime | None = None
    ) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"limit": min(max(page_size, 1), 100)}
        if job_id:
            params["shortcode"] = job_id
        if updated_after is not None:
            params["updated_after"] = format_spi_timestamp(updated_after)
        for payload in follow_next_pages(
            self._get,
            "candidates",
            initial_path="/candidates",
            initial_params=params,
        ):
            if not isinstance(payload, dict):
                raise ValueError("Workable candidate page contained a non-object item")
            candidate = map_candidate(payload)
            try:
                detail = self._candidate_detail(candidate.external_id)
                merged = {**payload, **detail}
            except EntityNotFoundError:
                merged = payload
            self._remember("candidate", candidate.external_id, merged)
            self._index_application(merged)
            yield merged

    def _candidate_detail(self, candidate_id: str) -> dict[str, Any]:
        try:
            payload = self._get(f"/candidates/{candidate_id}")
        except EntityNotFoundError as exc:
            raise EntityNotFoundError("candidate", candidate_id) from exc
        body = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else payload
        if not isinstance(body, dict):
            raise ValueError("Workable candidate detail was not an object")
        return body

    def _index_application(self, payload: dict[str, Any]) -> None:
        try:
            application = map_application(payload)
        except ValueError:
            return
        self._applications.setdefault(application.candidate_id, [])
        existing = [item.external_id for item in self._applications[application.candidate_id]]
        if application.external_id not in existing:
            self._applications[application.candidate_id].append(application)
        self._candidate_jobs[application.candidate_id] = application.job_id
        self._remember("application", application.external_id, payload)
        raw_account = payload.get("account")
        account = raw_account if isinstance(raw_account, dict) else {}
        name = account.get("name")
        if isinstance(name, str) and name.strip():
            self._account_name = name.strip()

    def _remember(self, object_type: str, external_id: str, payload: dict[str, Any]) -> None:
        self._raw[(object_type, external_id)] = payload

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{self._base_url}{path}"
        last_error: Exception | None = None
        attempts = max(self._retries, 0) + 1
        for attempt in range(attempts):
            self._wait_if_rate_window_exhausted()
            try:
                response = self._client.get(url, params=params)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise ProviderUnavailableError("Workable API is unreachable.") from exc
            self._note_rate_limit(response)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < attempts - 1:
                time.sleep(_retry_delay_seconds(response, attempt))
                if response.status_code == 429:
                    self._rate_remaining = None
                continue
            return self._parse_response(response, url)
        raise ProviderUnavailableError("Workable API is unreachable.") from last_error

    def _note_rate_limit(self, response: httpx.Response) -> None:
        remaining = _header(response, "X-Rate-Limit-Remaining")
        reset = _header(response, "X-Rate-Limit-Reset")
        if remaining is not None:
            try:
                self._rate_remaining = int(remaining)
            except ValueError:
                self._rate_remaining = None
        reset_at = _parse_reset_timestamp(reset)
        if reset_at is not None:
            self._rate_reset_at = reset_at

    def _wait_if_rate_window_exhausted(self) -> None:
        if self._rate_remaining is None or self._rate_remaining > 0:
            return
        delay = _seconds_until(self._rate_reset_at)
        if delay <= 0:
            self._rate_remaining = None
            return
        logger.info(
            "Workable rate window exhausted; waiting",
            extra={"extra_fields": {"delay_seconds": round(delay, 3)}},
        )
        time.sleep(delay)
        self._rate_remaining = None

    def _parse_response(self, response: httpx.Response, url: str) -> dict[str, Any]:
        path = urlparse(url).path
        logger.info(
            "Workable request",
            extra={"extra_fields": {"path": path, "status": response.status_code}},
        )
        if response.status_code in {401, 403}:
            raise ProviderConfigError("Workable rejected the access token or required scopes.")
        if response.status_code == 404:
            raise EntityNotFoundError("workable_resource", path)
        if response.status_code >= 400:
            raise ProviderUnavailableError(
                f"Workable API returned HTTP {response.status_code}.",
                status_code=response.status_code,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("Workable response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("Workable response was not an object")
        return payload


_MAX_RATE_WAIT_SECONDS = 30.0


def _header(response: httpx.Response, name: str) -> str | None:
    value = response.headers.get(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_reset_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed > 1_000_000_000_000:
        parsed /= 1000.0
    return parsed


def _seconds_until(reset_at: float | None, *, now: float | None = None) -> float:
    if reset_at is None:
        return 0.0
    current = time.time() if now is None else now
    delay = reset_at - current
    if delay <= 0:
        return 0.0
    return min(delay, _MAX_RATE_WAIT_SECONDS)


def _retry_delay_seconds(response: httpx.Response, attempt: int) -> float:
    if response.status_code == 429:
        reset_delay = _seconds_until(_parse_reset_timestamp(_header(response, "X-Rate-Limit-Reset")))
        if reset_delay > 0:
            return reset_delay
        retry_after = _header(response, "Retry-After")
        if retry_after is not None:
            try:
                parsed = float(retry_after)
            except ValueError:
                parsed = 0.0
            if parsed > 0:
                return min(parsed, _MAX_RATE_WAIT_SECONDS)
        return float(min(2**attempt, 16))
    return 0.05 * (attempt + 1)
