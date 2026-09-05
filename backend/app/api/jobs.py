"""
Job search API (spec section 35-37) + a manual "sync now" endpoint that
drains the mock source through the ingestion pipeline (Phase 7 replaces
manual sync with the automatic watcher, reusing the same ingestion code).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.connectors.mock_source import MockJobSource
from app.database.session import get_db
from app.models.job import Company, Job
from app.models.user import User
from app.schemas.job import JobListResponse, JobRead
from app.services.job_ingestion import ingest_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def search_jobs(
    q: str | None = None,
    employment_type: str | None = None,
    experience_level: str | None = None,
    remote: bool | None = None,
    location: str | None = None,
    source: str | None = None,
    skill: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Job).options(selectinload(Job.company))
    count_stmt = select(func.count()).select_from(Job)

    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Job.title).like(like) | func.lower(Job.description).like(like))
        count_stmt = count_stmt.where(func.lower(Job.title).like(like) | func.lower(Job.description).like(like))
    if employment_type:
        stmt = stmt.where(Job.employment_type == employment_type)
        count_stmt = count_stmt.where(Job.employment_type == employment_type)
    if experience_level:
        stmt = stmt.where(Job.experience_level == experience_level)
        count_stmt = count_stmt.where(Job.experience_level == experience_level)
    if remote is not None:
        stmt = stmt.where(Job.remote == remote)
        count_stmt = count_stmt.where(Job.remote == remote)
    if location:
        like_loc = f"%{location.lower()}%"
        stmt = stmt.where(func.lower(Job.location).like(like_loc))
        count_stmt = count_stmt.where(func.lower(Job.location).like(like_loc))
    if source:
        stmt = stmt.where(Job.source == source)
        count_stmt = count_stmt.where(Job.source == source)

    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Job.posted_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    jobs = list(result.scalars().all())

    if skill:
        jobs = [j for j in jobs if skill.lower() in [s.lower() for s in j.skills]]

    return JobListResponse(items=jobs, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/sync/mock", response_model=list[JobRead])
async def sync_mock_source(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Drains any unconsumed mock postings into the jobs table right now.
    Manual trigger for Phase 4; Phase 7's watcher calls the same pipeline
    automatically on an interval."""
    raw_jobs = await MockJobSource(db).fetch_jobs()
    ingested = []
    for raw in raw_jobs:
        job, _created = await ingest_job(db, raw, source="mock")
        ingested.append(job)

    if ingested:
        result = await db.execute(
            select(Job).options(selectinload(Job.company)).where(Job.id.in_([j.id for j in ingested]))
        )
        ingested = list(result.scalars().all())
    return ingested
