"""In-memory sample recruiting data for MockATSProvider.

IDs are stable so tests and the local dashboard stay consistent across restarts
of a single provider instance. Each MockATSProvider copies this dataset.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import TypedDict

from app.models.domain import (
    Application,
    Candidate,
    CandidateNote,
    InterviewFeedback,
    Job,
    Member,
    RecruitingEvent,
    Stage,
)
from app.models.enums import ApplicationStatus, EventType, JobStatus

DT = datetime
UTC_TZ = UTC


def _dt(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return DT(year, month, day, hour, 0, 0, tzinfo=UTC_TZ)


JOBS: list[Job] = [
    Job(
        id="job_backend_senior",
        external_id="job_backend_senior",
        title="Senior Backend Engineer",
        department="Engineering",
        location="Remote — Americas",
        status=JobStatus.OPEN,
        description=(
            "Build and operate API services in Python. Requirements: 5+ years backend "
            "experience, production FastAPI or equivalent, PostgreSQL, and comfort with "
            "observability. Nice to have: ATS/HRIS integrations, structured logging."
        ),
        created_at=_dt(2026, 7, 14),
        candidate_count=3,
    ),
    Job(
        id="job_recruiter",
        external_id="job_recruiter",
        title="Technical Recruiter",
        department="Talent",
        location="Santiago, Chile",
        status=JobStatus.OPEN,
        description=(
            "Own full-cycle recruiting for engineering roles. Requirements: experience "
            "sourcing technical candidates, pipeline hygiene in an ATS, and written "
            "briefs for hiring managers. Human judgment stays with the recruiter."
        ),
        created_at=_dt(2026, 8, 3),
        candidate_count=2,
    ),
    Job(
        id="job_pm",
        external_id="job_pm",
        title="Product Manager, Recruiting Tools",
        department="Product",
        location="New York, NY",
        status=JobStatus.OPEN,
        description=(
            "Define the workflow for an ATS-agnostic recruiting copilot. Requirements: "
            "shipped B2B workflow products, comfort with integrations, and evidence of "
            "working with recruiting or HR operators."
        ),
        created_at=_dt(2026, 6, 20),
        candidate_count=2,
    ),
    Job(
        id="job_platform_staff",
        external_id="job_platform_staff",
        title="Staff Platform Engineer",
        department="Engineering",
        location="London, UK",
        status=JobStatus.CLOSED,
        description=(
            "Lead platform reliability work. This role is closed and kept so the "
            "dashboard can show mixed job statuses."
        ),
        created_at=_dt(2026, 3, 2),
        candidate_count=1,
    ),
]

CANDIDATES: list[Candidate] = [
    Candidate(
        id="cand_alex_rivera",
        external_id="cand_alex_rivera",
        name="Alex Rivera",
        headline="Backend engineer — Python, FastAPI, Postgres",
        location="Austin, TX",
        email="alex.rivera@example.com",
        current_stage="Recruiter Review",
        created_at=_dt(2026, 9, 2, 15),
    ),
    Candidate(
        id="cand_sam_okonkwo",
        external_id="cand_sam_okonkwo",
        name="Sam Okonkwo",
        headline="Staff engineer, distributed systems",
        location="Toronto, ON",
        email="sam.okonkwo@example.com",
        current_stage="Hiring Manager Review",
        created_at=_dt(2026, 8, 28, 10),
    ),
    Candidate(
        id="cand_riley_nguyen",
        external_id="cand_riley_nguyen",
        name="Riley Nguyen",
        headline="Full-stack engineer, previously recruiting-tech startup",
        location="Remote",
        email="riley.nguyen@example.com",
        current_stage="Applied",
        created_at=_dt(2026, 9, 10, 9),
    ),
    Candidate(
        id="cand_jordan_hale",
        external_id="cand_jordan_hale",
        name="Jordan Hale",
        headline="Technical recruiter — infrastructure and ML hiring",
        location="Santiago, Chile",
        email="jordan.hale@example.com",
        current_stage="Recruiter Review",
        created_at=_dt(2026, 9, 5, 18),
    ),
    Candidate(
        id="cand_morgan_ellis",
        external_id="cand_morgan_ellis",
        name="Morgan Ellis",
        headline="Agency recruiter transitioning in-house",
        location="Buenos Aires, Argentina",
        email="morgan.ellis@example.com",
        current_stage="Interview",
        created_at=_dt(2026, 8, 18, 11),
    ),
    Candidate(
        id="cand_casey_brooks",
        external_id="cand_casey_brooks",
        name="Casey Brooks",
        headline="Product manager, HR workflow tools",
        location="Brooklyn, NY",
        email="casey.brooks@example.com",
        current_stage="Recruiter Review",
        created_at=_dt(2026, 9, 8, 14),
    ),
    Candidate(
        id="cand_taylor_kim",
        external_id="cand_taylor_kim",
        name="Taylor Kim",
        headline="PM — marketplace and B2B SaaS",
        location="New York, NY",
        email="taylor.kim@example.com",
        current_stage="Applied",
        created_at=_dt(2026, 9, 11, 16),
    ),
    Candidate(
        id="cand_lee_martinez",
        external_id="cand_lee_martinez",
        name="Lee Martinez",
        headline="Platform engineer — Kubernetes, observability",
        location="London, UK",
        email="lee.martinez@example.com",
        current_stage="Offer",
        created_at=_dt(2026, 4, 12, 9),
    ),
]

APPLICATIONS: list[Application] = [
    Application(
        id="app_alex_backend",
        external_id="app_alex_backend",
        candidate_id="cand_alex_rivera",
        job_id="job_backend_senior",
        stage="Recruiter Review",
        status=ApplicationStatus.ACTIVE,
    ),
    Application(
        id="app_sam_backend",
        external_id="app_sam_backend",
        candidate_id="cand_sam_okonkwo",
        job_id="job_backend_senior",
        stage="Hiring Manager Review",
        status=ApplicationStatus.ACTIVE,
    ),
    Application(
        id="app_riley_backend",
        external_id="app_riley_backend",
        candidate_id="cand_riley_nguyen",
        job_id="job_backend_senior",
        stage="Applied",
        status=ApplicationStatus.ACTIVE,
    ),
    Application(
        id="app_jordan_recruiter",
        external_id="app_jordan_recruiter",
        candidate_id="cand_jordan_hale",
        job_id="job_recruiter",
        stage="Recruiter Review",
        status=ApplicationStatus.ACTIVE,
    ),
    Application(
        id="app_morgan_recruiter",
        external_id="app_morgan_recruiter",
        candidate_id="cand_morgan_ellis",
        job_id="job_recruiter",
        stage="Interview",
        status=ApplicationStatus.ACTIVE,
    ),
    Application(
        id="app_casey_pm",
        external_id="app_casey_pm",
        candidate_id="cand_casey_brooks",
        job_id="job_pm",
        stage="Recruiter Review",
        status=ApplicationStatus.ACTIVE,
    ),
    Application(
        id="app_taylor_pm",
        external_id="app_taylor_pm",
        candidate_id="cand_taylor_kim",
        job_id="job_pm",
        stage="Applied",
        status=ApplicationStatus.ACTIVE,
    ),
    Application(
        id="app_lee_platform",
        external_id="app_lee_platform",
        candidate_id="cand_lee_martinez",
        job_id="job_platform_staff",
        stage="Offer",
        status=ApplicationStatus.ACTIVE,
    ),
]

STAGE_NAMES = [
    "Applied",
    "Recruiter Review",
    "Hiring Manager Review",
    "Interview",
    "Offer",
    "Hired",
]


def _stages_for(job_id: str) -> list[Stage]:
    return [
        Stage(
            id=f"{job_id}::stage_{index}",
            external_id=f"{job_id}::stage_{index}",
            job_id=job_id,
            name=name,
            position=index,
        )
        for index, name in enumerate(STAGE_NAMES)
    ]


STAGES: list[Stage] = []
for job in JOBS:
    STAGES.extend(_stages_for(job.external_id))

EVENTS: list[RecruitingEvent] = [
    RecruitingEvent(
        id="evt_alex_created",
        external_id="evt_alex_created",
        candidate_id="cand_alex_rivera",
        job_id="job_backend_senior",
        event_type=EventType.CANDIDATE_CREATED,
        timestamp=_dt(2026, 9, 2, 15),
        metadata={"source": "application_form"},
    ),
    RecruitingEvent(
        id="evt_alex_review",
        external_id="evt_alex_review",
        candidate_id="cand_alex_rivera",
        job_id="job_backend_senior",
        event_type=EventType.STAGE_CHANGED,
        timestamp=_dt(2026, 9, 4, 10),
        metadata={"from_stage": "Applied", "to_stage": "Recruiter Review"},
    ),
    RecruitingEvent(
        id="evt_sam_created",
        external_id="evt_sam_created",
        candidate_id="cand_sam_okonkwo",
        job_id="job_backend_senior",
        event_type=EventType.CANDIDATE_CREATED,
        timestamp=_dt(2026, 8, 28, 10),
        metadata={"source": "inbound"},
    ),
    RecruitingEvent(
        id="evt_jordan_created",
        external_id="evt_jordan_created",
        candidate_id="cand_jordan_hale",
        job_id="job_recruiter",
        event_type=EventType.CANDIDATE_CREATED,
        timestamp=_dt(2026, 9, 5, 18),
        metadata={"source": "linkedin"},
    ),
    RecruitingEvent(
        id="evt_casey_created",
        external_id="evt_casey_created",
        candidate_id="cand_casey_brooks",
        job_id="job_pm",
        event_type=EventType.CANDIDATE_CREATED,
        timestamp=_dt(2026, 9, 8, 14),
        metadata={"source": "referral"},
    ),
    RecruitingEvent(
        id="evt_lee_offer",
        external_id="evt_lee_offer",
        candidate_id="cand_lee_martinez",
        job_id="job_platform_staff",
        event_type=EventType.STAGE_CHANGED,
        timestamp=_dt(2026, 5, 1, 16),
        metadata={"from_stage": "Interview", "to_stage": "Offer"},
    ),
]

FEEDBACK: list[InterviewFeedback] = [
    InterviewFeedback(
        id="fb_morgan_1",
        external_id="fb_morgan_1",
        candidate_id="cand_morgan_ellis",
        job_id="job_recruiter",
        interviewer="Pat Singh",
        summary=(
            "Walked through a recent engineering search. Evidence of structured "
            "intake notes. Follow-up needed on how they report pipeline health."
        ),
        submitted_at=_dt(2026, 9, 1, 17),
    )
]

MEMBERS: list[Member] = [
    Member(
        id="mem_pat_singh",
        external_id="mem_pat_singh",
        name="Pat Singh",
        email="pat.singh@example.com",
        role="Hiring Manager",
    ),
    Member(
        id="mem_avery_cole",
        external_id="mem_avery_cole",
        name="Avery Cole",
        email="avery.cole@example.com",
        role="Recruiter",
    ),
]


class MockSnapshot(TypedDict):
    jobs: list[Job]
    candidates: list[Candidate]
    applications: list[Application]
    stages: list[Stage]
    events: list[RecruitingEvent]
    feedback: list[InterviewFeedback]
    members: list[Member]
    notes: list[CandidateNote]


def snapshot() -> MockSnapshot:
    return {
        "jobs": deepcopy(JOBS),
        "candidates": deepcopy(CANDIDATES),
        "applications": deepcopy(APPLICATIONS),
        "stages": deepcopy(STAGES),
        "events": deepcopy(EVENTS),
        "feedback": deepcopy(FEEDBACK),
        "members": deepcopy(MEMBERS),
        "notes": [],
    }
