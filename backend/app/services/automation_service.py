"""
Bridges a "ready_for_review" Application to the Phase 8 browser automator
and records an honest outcome either way — this is the one place that
decides whether an application is allowed to move to "submitted" at all.

Automation is only ever attempted for source="mock" jobs. Every other
source is refused outright rather than silently skipped, because this
build must never even attempt browser automation against a real job
portal (spec section 6/51) — Phase 7's Rapid Apply pipeline still creates
the Application for real-source jobs, it just always leaves them for a
human to submit manually.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.automation.browser_automation import AutomationResult, run_application_automation
from app.core.config import settings
from app.core.logging import get_logger
from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User
from app.services.notification_service import notify
from app.services.profile_service import get_or_create_profile

logger = get_logger(__name__)


async def _primary_resume(db: AsyncSession, user_id) -> Resume | None:
    result = await db.execute(
        select(Resume).where(Resume.user_id == user_id, Resume.is_primary.is_(True))
    )
    resume = result.scalar_one_or_none()
    if resume is not None:
        return resume
    # No resume explicitly marked primary yet — fall back to the most
    # recently uploaded one rather than refusing to automate outright.
    result = await db.execute(
        select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
    )
    return result.scalars().first()


async def _matched_skills(db: AsyncSession, user_id, job_id) -> list[str]:
    result = await db.execute(
        select(JobMatch.matched_skills).where(JobMatch.user_id == user_id, JobMatch.job_id == job_id)
    )
    matched = result.scalar_one_or_none()
    return matched or []


async def attempt_submission(db: AsyncSession, application: Application, job: Job, user: User) -> AutomationResult:
    # Always ensure job.company is loaded before either branch below builds
    # a notification message from it — the caller isn't guaranteed to have
    # fetched it eagerly (e.g. the manual /auto-submit endpoint doesn't).
    job_result = await db.execute(select(Job).options(selectinload(Job.company)).where(Job.id == job.id))
    job = job_result.scalar_one()

    if job.source != "mock":
        result = AutomationResult(status="failsafe_stopped", reason="automation_not_permitted_for_source")
        application.status = "needs_manual_review"
        application.events.append(
            ApplicationEvent(
                event_type="automation_failsafe",
                message=(
                    f"Automation only runs against mock/testable sources; '{job.source}' jobs are always "
                    "completed manually — this build never automates a real job portal."
                ),
            )
        )
        await notify(
            db,
            user.id,
            type="needs_manual_review",
            title="Application needs your review",
            message=f"'{job.source}' jobs are always completed manually — {job.title} at {job.company.name} is ready for you.",
            application_id=application.id,
        )
        await db.commit()
        return result

    profile = await get_or_create_profile(db, user)
    resume = await _primary_resume(db, user.id)
    matched_skills = await _matched_skills(db, user.id, job.id)

    form_url = f"{settings.MOCK_FORM_BASE_URL}/api/mock-forms/{job.id}"
    result = await run_application_automation(form_url, profile, user, resume, job, matched_skills)

    if result.status == "submitted":
        application.status = "submitted"
        application.applied_at = datetime.now(timezone.utc)
        application.events.append(
            ApplicationEvent(
                event_type="status_changed",
                message=(
                    f"Rapid Apply automation submitted this application "
                    f"(fields filled: {', '.join(result.filled_fields) or 'none required'})."
                ),
            )
        )
        logger.info("automation_application_submitted", application_id=str(application.id))
        await notify(
            db,
            user.id,
            type="application_submitted",
            title="Application submitted",
            message=f"Rapid Apply submitted your application to {job.title} at {job.company.name}.",
            application_id=application.id,
        )
    else:
        application.status = "needs_manual_review"
        reason = result.reason or "unknown_error"
        application.events.append(
            ApplicationEvent(
                event_type="automation_failsafe",
                message=(
                    f"Automation stopped before submitting ({reason}) — falling back to manual completion, "
                    "as this build never guesses at CAPTCHA/MFA or an unrecognized required field."
                ),
            )
        )
        logger.info("automation_needs_manual_review", application_id=str(application.id), reason=reason)
        await notify(
            db,
            user.id,
            type="needs_manual_review",
            title="Application needs your review",
            message=f"Automation couldn't finish applying to {job.title} at {job.company.name} ({reason}).",
            application_id=application.id,
        )

    await db.commit()
    return result
