"""
Orchestrates the fast-filter -> match-score -> explanation pipeline (spec
section 26) and persists the result. Reused by the manual API in Phase 5
and by the Rapid Apply worker in Phase 7 — one code path, one behavior.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.matching_engine import compute_match, explain_match
from app.ai.base import AIProvider
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User
from app.services.eligibility import check_eligibility
from app.services.profile_service import get_or_create_profile


async def _primary_resume_skills(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(Resume).where(Resume.user_id == user_id, Resume.is_primary.is_(True))
    )
    resume = result.scalar_one_or_none()
    if resume and resume.parsed_data:
        return resume.parsed_data.get("skills", [])
    return []


async def compute_and_store_match(
    db: AsyncSession, user: User, job: Job, ai: AIProvider
) -> JobMatch:
    profile = await get_or_create_profile(db, user)
    resume_skills = await _primary_resume_skills(db, user.id)

    eligibility = check_eligibility(profile, job)
    breakdown = compute_match(profile, job, resume_skills)
    explanation = await explain_match(breakdown, job, ai)

    result = await db.execute(
        select(JobMatch).where(JobMatch.user_id == user.id, JobMatch.job_id == job.id)
    )
    match = result.scalar_one_or_none()
    if match is None:
        match = JobMatch(user_id=user.id, job_id=job.id)
        db.add(match)

    match.overall_score = breakdown.overall_score
    match.skills_score = breakdown.skills_score
    match.education_score = breakdown.education_score
    match.experience_score = breakdown.experience_score
    match.location_score = breakdown.location_score
    match.role_score = breakdown.role_score
    match.matched_skills = breakdown.matched_skills
    match.missing_skills = breakdown.missing_skills
    match.explanation = explanation
    match.is_eligible = eligibility.passed
    match.eligibility_reasons = eligibility.reasons

    await db.commit()
    await db.refresh(match)
    return match


async def get_job_with_company(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == job_id)
    )
    return result.scalar_one_or_none()


async def get_profile_for_matching(db: AsyncSession, user: User) -> Profile:
    profile = await get_or_create_profile(db, user)
    return profile
