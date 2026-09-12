from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models.domain import Application, Candidate, FileMetadata, Job, RecruitingEvent, Stage
from app.models.enums import ApplicationStatus, EventType, JobStatus
from app.sync.hashing import stable_hash

_JOB_STATE = {
    "published": JobStatus.OPEN,
    "draft": JobStatus.DRAFT,
    "closed": JobStatus.CLOSED,
    "archived": JobStatus.ARCHIVED,
}

_STAGE_ACTIONS = {
    "applied",
    "sourced",
    "shortlisted",
    "assessment",
    "phone-screen",
    "interview",
    "offer",
    "hired",
    "moved",
    "move",
}


def parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return datetime.now(UTC)


def map_location(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if not isinstance(value, dict):
        return None
    if isinstance(value.get("location_str"), str) and value["location_str"].strip():
        location_str: str = value["location_str"]
        return location_str.strip()
    parts = [value.get("city"), value.get("region"), value.get("country")]
    joined = ", ".join(str(part) for part in parts if isinstance(part, str) and part.strip())
    return joined or None


def map_job(payload: dict[str, Any]) -> Job:
    shortcode = payload.get("shortcode") or payload.get("id")
    if not shortcode:
        raise ValueError("Workable job is missing shortcode and id")
    external_id = str(shortcode)
    state = str(payload.get("state") or "published")
    description = payload.get("description") or payload.get("full_description")
    if description is not None:
        description = str(description)
    return Job(
        id=external_id,
        external_id=external_id,
        title=str(payload.get("title") or payload.get("full_title") or "Untitled job"),
        department=str(payload["department"]) if payload.get("department") else None,
        location=map_location(payload.get("location")),
        status=_JOB_STATE.get(state, JobStatus.OPEN),
        description=description,
        created_at=parse_datetime(payload.get("created_at")),
    )


def map_candidate(payload: dict[str, Any]) -> Candidate:
    candidate_id = payload.get("id")
    if not candidate_id:
        raise ValueError("Workable candidate is missing id")
    external_id = str(candidate_id)
    skills = _string_list(payload.get("skills"))
    tags = _string_list(payload.get("tags"))
    social = []
    for item in payload.get("social_profiles") or []:
        if not isinstance(item, dict):
            continue
        social.append(
            {
                "network": item.get("type"),
                "name": item.get("name"),
                "url": item.get("url"),
            }
        )
    experience = [item for item in (payload.get("experience_entries") or []) if isinstance(item, dict)]
    education = [item for item in (payload.get("education_entries") or []) if isinstance(item, dict)]
    source = payload.get("common_source") or payload.get("domain")
    if payload.get("sourced") is True and not source:
        source = "sourced"
    return Candidate(
        id=external_id,
        external_id=external_id,
        name=str(payload.get("name") or "Unnamed candidate"),
        headline=str(payload["headline"]) if payload.get("headline") else None,
        location=map_location(payload.get("location"))
        or (str(payload["address"]) if payload.get("address") else None),
        email=str(payload["email"]) if payload.get("email") else None,
        phone=str(payload["phone"]) if payload.get("phone") else None,
        current_stage=str(payload["stage"]) if payload.get("stage") else None,
        created_at=parse_datetime(payload.get("created_at")),
        summary=str(payload["summary"]) if payload.get("summary") else None,
        skills=skills,
        tags=tags,
        source=str(source) if source else None,
        social_links=social,
        experience=experience,
        education=education,
    )


def map_application(payload: dict[str, Any]) -> Application:
    candidate_id = payload.get("id")
    raw_job = payload.get("job")
    job: dict[str, Any] = raw_job if isinstance(raw_job, dict) else {}
    shortcode = job.get("shortcode")
    if not candidate_id:
        raise ValueError("Workable candidate application is missing candidate id")
    if not shortcode:
        raise ValueError("Workable candidate application is missing job.shortcode")
    external_id = f"{candidate_id}:{shortcode}"
    return Application(
        id=external_id,
        external_id=external_id,
        candidate_id=str(candidate_id),
        job_id=str(shortcode),
        stage=str(payload["stage"]) if payload.get("stage") else None,
        status=_application_status(payload),
        created_at=parse_datetime(payload.get("created_at")),
    )


def map_stage(payload: dict[str, Any], *, job_id: str | None = None) -> Stage:
    slug = payload.get("slug") or payload.get("id") or payload.get("name")
    if not slug:
        raise ValueError("Workable stage is missing slug")
    external_id = f"{job_id}:{slug}" if job_id else str(slug)
    position = payload.get("position")
    return Stage(
        id=external_id,
        external_id=external_id,
        job_id=job_id,
        name=str(payload.get("name") or slug),
        position=int(position) if isinstance(position, int) else 0,
    )


def map_activity(payload: dict[str, Any], *, candidate_id: str, job_id: str | None) -> RecruitingEvent:
    action = str(payload.get("action") or "other")
    created = parse_datetime(payload.get("created_at") or payload.get("updated_at"))
    raw_member = payload.get("member")
    member: dict[str, Any] = raw_member if isinstance(raw_member, dict) else {}
    basis = {
        "candidate": candidate_id,
        "action": action,
        "created_at": payload.get("created_at"),
        "stage": payload.get("stage_name"),
        "member": member.get("id"),
        "body_digest": stable_hash(payload.get("body") or "")[:16],
    }
    external_id = stable_hash(basis)[:32]
    metadata: dict[str, Any] = {"action": action}
    if payload.get("stage_name"):
        metadata["stage_name"] = payload.get("stage_name")
    if member.get("name"):
        metadata["member_name"] = member.get("name")
    raw_target = payload.get("target_stage")
    target: dict[str, Any] = raw_target if isinstance(raw_target, dict) else {}
    if target.get("name"):
        metadata["to_stage"] = target.get("name")
    return RecruitingEvent(
        id=external_id,
        external_id=external_id,
        candidate_id=candidate_id,
        job_id=job_id,
        event_type=_event_type(action),
        timestamp=created,
        metadata=metadata,
    )


def map_file(payload: dict[str, Any], *, candidate_id: str) -> FileMetadata:
    name = payload.get("name")
    if not name:
        raise ValueError("Workable file is missing name")
    source = payload.get("source") or payload.get("kind")
    external_id = stable_hash({"candidate": candidate_id, "name": name, "source": source})[:32]
    created = None
    if payload.get("created_at"):
        created = parse_datetime(payload.get("created_at"))
    return FileMetadata(
        id=external_id,
        external_id=external_id,
        candidate_id=candidate_id,
        filename=str(name),
        file_type=str(payload["kind"]) if payload.get("kind") else None,
        source_ref=str(source) if source else None,
        created_at=created,
    )


def sanitize_file_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(payload)
    if "preview_url" in cleaned:
        cleaned.pop("preview_url")
        cleaned["preview_url_omitted"] = True
    return cleaned


def _application_status(payload: dict[str, Any]) -> ApplicationStatus:
    if payload.get("withdrew"):
        return ApplicationStatus.WITHDRAWN
    if payload.get("disqualified"):
        return ApplicationStatus.REJECTED
    stage = str(payload.get("stage") or "").lower()
    kind = str(payload.get("stage_kind") or "").lower()
    if payload.get("hired_at") or stage == "hired" or kind == "hired":
        return ApplicationStatus.HIRED
    return ApplicationStatus.ACTIVE


def _event_type(action: str) -> EventType:
    lowered = action.lower()
    if lowered in {"applied", "sourced"}:
        return EventType.CANDIDATE_CREATED
    if lowered in _STAGE_ACTIONS:
        return EventType.STAGE_CHANGED
    if lowered in {"comment"}:
        return EventType.NOTE_ADDED
    if lowered in {"event", "interview-scheduled", "scheduled"}:
        return EventType.INTERVIEW_SCHEDULED
    if lowered in {"rating"}:
        return EventType.FEEDBACK_SUBMITTED
    return EventType.OTHER


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            items.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("skill")
            if isinstance(name, str) and name.strip():
                items.append(name.strip())
    return items
