"""
Matching API — spec section 17/36. Scores are always computed by
app/agents/matching_engine.py (deterministic) — this layer only handles
persistence, auth, and listing/filtering.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.factory import get_ai_provider
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user import User
from app.schemas.job_match import JobMatchRead
from app.services.match_service import compute_and_store_match, get_job_with_company

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/compute/{job_id}", response_model=JobMatchRead)
async def compute_match_for_job(
    job_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    job = await get_job_with_company(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    match = await compute_and_store_match(db, user, job, get_ai_provider())
    match.job = job
    return match


@router.post("/compute-all", response_model=list[JobMatchRead])
async def compute_matches_for_all_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scores every job the user hasn't been matched against yet. Rapid
    Apply (Phase 7) scores one job at a time as it's detected instead —
    this bulk endpoint is for browsing /jobs with match scores visible."""
    already_matched = select(JobMatch.job_id).where(JobMatch.user_id == user.id)
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.company))
        .where(Job.id.notin_(already_matched))
        .order_by(Job.posted_at.desc())
        .limit(limit)
    )
    jobs = list(result.scalars().all())

    ai = get_ai_provider()
    matches = []
    for job in jobs:
        match = await compute_and_store_match(db, user, job, ai)
        match.job = job
        matches.append(match)
    return matches


@router.get("", response_model=list[JobMatchRead])
async def list_matches(
    min_score: int = Query(default=0, ge=0, le=100),
    eligible_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(JobMatch)
        .options(selectinload(JobMatch.job).selectinload(Job.company))
        .where(JobMatch.user_id == user.id, JobMatch.overall_score >= min_score)
        .order_by(JobMatch.overall_score.desc())
    )
    if eligible_only:
        stmt = stmt.where(JobMatch.is_eligible.is_(True))

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{job_id}", response_model=JobMatchRead)
async def get_match_for_job(
    job_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(JobMatch)
        .options(selectinload(JobMatch.job).selectinload(Job.company))
        .where(JobMatch.user_id == user.id, JobMatch.job_id == job_id)
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No match computed for this job yet")
    return match
