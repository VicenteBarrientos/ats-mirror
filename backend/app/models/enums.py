from enum import StrEnum


class JobStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ApplicationStatus(StrEnum):
    ACTIVE = "active"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class AutomationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class EventType(StrEnum):
    CANDIDATE_CREATED = "candidate_created"
    STAGE_CHANGED = "stage_changed"
    NOTE_ADDED = "note_added"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    OTHER = "other"


class SyncRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class Capability(StrEnum):
    READ_JOBS = "read_jobs"
    READ_CANDIDATES = "read_candidates"
    READ_STAGES = "read_stages"
    MOVE_CANDIDATE = "move_candidate"
    ADD_NOTE = "add_note"
    READ_FEEDBACK = "read_feedback"
    WEBHOOKS = "webhooks"
    SEARCH_CANDIDATES = "search_candidates"
    READ_EVENTS = "read_events"
    READ_MEMBERS = "read_members"
    READ_FILES_METADATA = "read_files_metadata"
