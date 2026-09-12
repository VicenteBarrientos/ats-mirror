"""Content-hash semantics for ATS Mirror.

`content_hash` is a SHA-256 of **source-controlled content only**.

It MUST include:
- normalized fields that come from the ATS (title, email, stage, …)
- durable source identifiers (`external_id`)
- source timestamps such as Workable `updated_at` / `created_at`

It MUST NOT include:
- ATS Mirror internal UUIDs (`id`)
- `connection_id`
- `last_synced_at` / `last_seen_at` / `synced_at`
- local `updated_at` clocks
- sync run ids
- derived list-view fields (`candidate_count`, `job_title`, `last_event_*`)
- future local annotations or AI fields
- temporary URLs (`preview_url`)
- secrets (tokens, Authorization headers)

Repeated ingestion of the same source object therefore produces the same hash
even if sync metadata differs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from app.models.domain import Application, Candidate, FileMetadata, Job, RecruitingEvent, Stage

_LOCAL_METADATA_KEYS = frozenset(
    {
        "connection_id",
        "last_synced_at",
        "last_seen_at",
        "synced_at",
        "fetched_at",
        "candidate_count",
        "job_title",
        "last_event_at",
        "last_event_type",
    }
)

_SECRET_OR_VOLATILE_KEYS = frozenset(
    {
        "preview_url",
        "access_token",
        "authorization",
        "token",
        "api_key",
        "password",
        "secret",
        "bearer",
    }
)

_JOB_FIELDS = (
    "external_id",
    "title",
    "department",
    "location",
    "status",
    "description",
    "created_at",
)
_CANDIDATE_FIELDS = (
    "external_id",
    "name",
    "headline",
    "location",
    "email",
    "phone",
    "current_stage",
    "created_at",
    "summary",
    "skills",
    "tags",
    "source",
    "social_links",
    "experience",
    "education",
)
_APPLICATION_FIELDS = ("external_id", "candidate_id", "job_id", "stage", "status", "created_at")
_EVENT_FIELDS = ("external_id", "candidate_id", "job_id", "event_type", "timestamp", "metadata")
_STAGE_FIELDS = ("external_id", "job_id", "name", "position")
_FILE_FIELDS = ("external_id", "candidate_id", "filename", "file_type", "source_ref", "created_at")


def stable_hash(value: Any) -> str:
    """SHA-256 of canonical JSON (sorted keys, no whitespace)."""
    payload = json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def raw_content_hash(payload: dict[str, Any]) -> str:
    """Hash a source ATS payload after dropping secrets and local metadata."""
    return stable_hash(_strip_keys(payload, _LOCAL_METADATA_KEYS | _SECRET_OR_VOLATILE_KEYS))


def canonical_content_hash(object_type: str, entity: object) -> str:
    """Hash normalized fields for a domain object. Ignores internal identity/sync metadata."""
    if hasattr(entity, "model_dump"):
        dumped = entity.model_dump(mode="json")
    elif isinstance(entity, dict):
        dumped = dict(entity)
    else:
        raise TypeError(f"Cannot hash {type(entity)!r}")
    if not isinstance(dumped, dict):
        raise TypeError("Canonical hash input must dump to a dict")
    fields = _fields_for(object_type)
    selected = {key: dumped.get(key) for key in fields}
    return stable_hash(selected)


def canonical_job_hash(job: Job) -> str:
    return canonical_content_hash("job", job)


def canonical_candidate_hash(candidate: Candidate) -> str:
    return canonical_content_hash("candidate", candidate)


def canonical_application_hash(application: Application) -> str:
    return canonical_content_hash("application", application)


def canonical_event_hash(event: RecruitingEvent) -> str:
    return canonical_content_hash("event", event)


def canonical_stage_hash(stage: Stage) -> str:
    return canonical_content_hash("stage", stage)


def canonical_file_hash(file_meta: FileMetadata) -> str:
    return canonical_content_hash("file", file_meta)


def _fields_for(object_type: str) -> tuple[str, ...]:
    mapping = {
        "job": _JOB_FIELDS,
        "candidate": _CANDIDATE_FIELDS,
        "application": _APPLICATION_FIELDS,
        "event": _EVENT_FIELDS,
        "stage": _STAGE_FIELDS,
        "file": _FILE_FIELDS,
    }
    return mapping.get(object_type, ())


def _strip_keys(value: Any, banned: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_keys(item, banned)
            for key, item in value.items()
            if str(key).lower() not in banned
        }
    if isinstance(value, list):
        return [_strip_keys(item, banned) for item in value]
    return value


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
