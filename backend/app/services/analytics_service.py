"""
Analytics engine — spec section 11 (Phase 11): application funnel,
conversion rates, resume performance, and a submissions-over-time series.

Everything here reads from data other phases already wrote — no new
tracking is introduced. In particular the funnel is built from
ApplicationEvent history (not just Application.status, the *current*
state) so that an application which reached "interview" before later
being "rejected" still counts as having reached the interview stage: the
funnel measures how far applications got, not where they ended up.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import RESPONSE_STATUSES, Application, ApplicationEvent
from app.models.resume import Resume

#: Canonical funnel order (spec section 31's application lifecycle,
#: collapsing the two Phase 8 outcomes "submitted" and
#: "needs_manual_review" into one "reached submission" stage since both
#: mean the application was fully prepared and handed off).
FUNNEL_STAGES = [
    "discovered",
    "matched",
    "saved",
    "preparing",
    "ready_for_review",
    "submitted",
    "assessment",
    "interview",
    "offer",
]

#: Statuses that count toward the "submitted" funnel stage even though
#: they aren't spelled "submitted" — Phase 8's honest failsafe outcome
#: still means the application was fully prepared and reached a human
#: decision point, which is what the funnel stage represents.
_SUBMITTED_ALIASES = {"submitted", "needs_manual_review"}

_STATUS_CHANGE_RE = re.compile(r"to '([a-z_]+)'$")
_CREATED_WITH_RE = re.compile(r"created with status '([a-z_]+)'$")


@dataclass
class FunnelStage:
    name: str
    count: int


@dataclass
class FunnelResult:
    total_applications: int
    stages: list[FunnelStage] = field(default_factory=list)
    submitted_rate: float | None = None
    response_rate: float | None = None
    interview_rate: float | None = None
    offer_rate: float | None = None


@dataclass
class ResumePerformance:
    resume_id: str
    label: str
    total_applications: int
    submitted: int
    responses: int
    interviews: int
    offers: int
    avg_match_score: float | None
    response_rate: float | None


@dataclass
class TimelinePoint:
    date: str
    discovered: int
    submitted: int


@dataclass
class AnalyticsSummary:
    total_applications: int
    total_submitted: int
    total_interviews: int
    total_offers: int
    avg_match_score: float | None
    avg_days_to_submit: float | None


def _statuses_reached(application: Application) -> set[str]:
    """Every status this application has ever been in, reconstructed from
    its event log plus its current status (belt-and-suspenders in case an
    application was created with no explicit event, which shouldn't
    happen but must never silently undercount)."""
    reached = {application.status}
    for event in application.events:
        if event.event_type != "status_changed":
            continue
        match = _STATUS_CHANGE_RE.search(event.message) or _CREATED_WITH_RE.search(event.message)
        if match:
            reached.add(match.group(1))
    return reached


def _reached_submission(statuses: set[str]) -> bool:
    return bool(statuses & _SUBMITTED_ALIASES)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    """SQLite (used in tests) doesn't preserve tzinfo on
    DateTime(timezone=True) columns the way Postgres does, so a value
    round-tripped through it can come back naive. Treat any naive value as
    UTC (everything in this app is written in UTC) so comparisons against
    timezone-aware datetimes never raise."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def _load_applications(db: AsyncSession, user_id) -> list[Application]:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.events))
        .where(Application.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_funnel(db: AsyncSession, user_id) -> FunnelResult:
    applications = await _load_applications(db, user_id)
    total = len(applications)

    stage_counts: dict[str, int] = {stage: 0 for stage in FUNNEL_STAGES}
    per_app_reached: list[set[str]] = []

    for application in applications:
        reached = _statuses_reached(application)
        per_app_reached.append(reached)
        for stage in FUNNEL_STAGES:
            if stage == "submitted":
                if _reached_submission(reached):
                    stage_counts[stage] += 1
            elif stage in reached:
                stage_counts[stage] += 1

    stages = [FunnelStage(name=stage, count=stage_counts[stage]) for stage in FUNNEL_STAGES]

    submitted_count = stage_counts["submitted"]
    response_count = sum(1 for reached in per_app_reached if reached & RESPONSE_STATUSES)
    interview_count = sum(1 for reached in per_app_reached if reached & {"interview", "offer"})
    offer_count = stage_counts["offer"]

    def rate(numerator: int, denominator: int) -> float | None:
        if denominator == 0:
            return None
        return round(100 * numerator / denominator, 1)

    return FunnelResult(
        total_applications=total,
        stages=stages,
        submitted_rate=rate(submitted_count, total),
        response_rate=rate(response_count, submitted_count),
        interview_rate=rate(interview_count, submitted_count),
        offer_rate=rate(offer_count, interview_count),
    )


async def get_resume_performance(db: AsyncSession, user_id) -> list[ResumePerformance]:
    applications = await _load_applications(db, user_id)

    resumes_result = await db.execute(select(Resume).where(Resume.user_id == user_id))
    resumes_by_id = {str(r.id): r for r in resumes_result.scalars().all()}

    grouped: dict[str | None, list[Application]] = defaultdict(list)
    for application in applications:
        grouped[str(application.resume_id) if application.resume_id else None].append(application)

    performance: list[ResumePerformance] = []
    for resume_id, apps in grouped.items():
        if resume_id is None:
            continue  # No resume attached yet — nothing meaningful to attribute.
        resume = resumes_by_id.get(resume_id)
        if resume is None:
            continue  # Resume was deleted; its applications aren't attributable anymore.

        reached_per_app = [_statuses_reached(a) for a in apps]
        submitted = sum(1 for r in reached_per_app if _reached_submission(r))
        responses = sum(1 for r in reached_per_app if r & RESPONSE_STATUSES)
        interviews = sum(1 for r in reached_per_app if r & {"interview", "offer"})
        offers = sum(1 for r in reached_per_app if "offer" in r)
        scores = [a.match_score for a in apps if a.match_score is not None]

        performance.append(
            ResumePerformance(
                resume_id=resume_id,
                label=resume.label,
                total_applications=len(apps),
                submitted=submitted,
                responses=responses,
                interviews=interviews,
                offers=offers,
                avg_match_score=round(sum(scores) / len(scores), 1) if scores else None,
                response_rate=round(100 * responses / submitted, 1) if submitted else None,
            )
        )

    performance.sort(key=lambda p: p.total_applications, reverse=True)
    return performance


async def get_timeline(db: AsyncSession, user_id, days: int = 30) -> list[TimelinePoint]:
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    applications = await _load_applications(db, user_id)

    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"discovered": 0, "submitted": 0})

    for application in applications:
        discovered_at = _as_aware_utc(application.discovered_at)
        applied_at = _as_aware_utc(application.applied_at)
        if discovered_at and discovered_at >= since:
            key = discovered_at.date().isoformat()
            by_day[key]["discovered"] += 1
        if applied_at and applied_at >= since:
            key = applied_at.date().isoformat()
            by_day[key]["submitted"] += 1

    points: list[TimelinePoint] = []
    for i in range(days):
        day = (since + timedelta(days=i)).date().isoformat()
        counts = by_day.get(day, {"discovered": 0, "submitted": 0})
        points.append(TimelinePoint(date=day, discovered=counts["discovered"], submitted=counts["submitted"]))
    return points


async def get_summary(db: AsyncSession, user_id) -> AnalyticsSummary:
    applications = await _load_applications(db, user_id)
    total = len(applications)

    reached_per_app = [_statuses_reached(a) for a in applications]
    total_submitted = sum(1 for r in reached_per_app if _reached_submission(r))
    total_interviews = sum(1 for r in reached_per_app if r & {"interview", "offer"})
    total_offers = sum(1 for r in reached_per_app if "offer" in r)

    scores = [a.match_score for a in applications if a.match_score is not None]
    avg_match_score = round(sum(scores) / len(scores), 1) if scores else None

    submit_days = [
        (_as_aware_utc(a.applied_at) - _as_aware_utc(a.discovered_at)).total_seconds() / 86400
        for a in applications
        if a.applied_at is not None and a.discovered_at is not None
    ]
    avg_days_to_submit = round(sum(submit_days) / len(submit_days), 2) if submit_days else None

    return AnalyticsSummary(
        total_applications=total,
        total_submitted=total_submitted,
        total_interviews=total_interviews,
        total_offers=total_offers,
        avg_match_score=avg_match_score,
        avg_days_to_submit=avg_days_to_submit,
    )
