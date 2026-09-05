"""
Automation control enforcement — spec sections 60-62. Every check here is a
hard stop: none of it is skippable by a high match score, and all of it
runs before a job is ever queued. `screening_block_reason` is the single
gate app/services/rapid_apply_service.detect_and_enqueue calls per
(user, job) pair before it will even compute a match.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.automation import AutomationRule
from app.models.job import Job
from app.models.user import User


async def get_or_create_rule(db: AsyncSession, user: User) -> AutomationRule:
    result = await db.execute(select(AutomationRule).where(AutomationRule.user_id == user.id))
    rule = result.scalar_one_or_none()
    if rule is None:
        rule = AutomationRule(user_id=user.id)
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
    return rule


def _matches_any_keyword(text: str, keywords: list[str]) -> str | None:
    lowered = text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered:
            return keyword
    return None


def blocklist_reason(rule: AutomationRule, job: Job) -> str | None:
    """Deterministic, no DB access — checked first since it's free."""
    if job.source in rule.blocked_sources:
        return f"source_blocked:{job.source}"

    company_match = _matches_any_keyword(job.company.name, rule.blocked_companies)
    if company_match:
        return f"company_blocked:{company_match}"

    haystack = f"{job.title} {job.description or ''}"
    keyword_match = _matches_any_keyword(haystack, rule.blocked_keywords)
    if keyword_match:
        return f"keyword_blocked:{keyword_match}"

    return None


@dataclass
class RateLimitStatus:
    exceeded: bool
    reason: str | None = None


async def rate_limit_status(db: AsyncSession, rule: AutomationRule, user_id, job: Job) -> RateLimitStatus:
    now = datetime.now(timezone.utc)

    if rule.max_applications_per_hour is not None:
        count = await db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == user_id, Application.discovered_at >= now - timedelta(hours=1))
        )
        if count >= rule.max_applications_per_hour:
            return RateLimitStatus(True, "max_applications_per_hour")

    if rule.max_applications_per_day is not None:
        count = await db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == user_id, Application.discovered_at >= now - timedelta(days=1))
        )
        if count >= rule.max_applications_per_day:
            return RateLimitStatus(True, "max_applications_per_day")

    if rule.max_applications_per_company is not None:
        count = await db.scalar(
            select(func.count())
            .select_from(Application)
            .join(Job, Job.id == Application.job_id)
            .where(Application.user_id == user_id, Job.company_id == job.company_id)
        )
        if count >= rule.max_applications_per_company:
            return RateLimitStatus(True, "max_applications_per_company")

    return RateLimitStatus(False)


async def screening_block_reason(db: AsyncSession, rule: AutomationRule, user_id, job: Job) -> str | None:
    """Single entry point: returns a reason string if this job must never
    be queued for this user right now, or None if it's clear to proceed to
    eligibility/matching. Order matters only for which reason is reported —
    every check still runs against the real, current state each time."""
    if rule.state != "running":
        return f"automation_{rule.state}"

    blocked = blocklist_reason(rule, job)
    if blocked:
        return blocked

    rate_status = await rate_limit_status(db, rule, user_id, job)
    if rate_status.exceeded:
        return f"rate_limit:{rate_status.reason}"

    return None
