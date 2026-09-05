"""
Rapid Apply API — spec sections 57/58. `POST /run-cycle` triggers one full
detect->match->queue->process cycle synchronously and returns counts,
which is what makes this endpoint (and the whole pipeline) directly
testable without a running Celery worker; the same `run_cycle()` function
is what `app.worker.tasks.run_rapid_apply_cycle` calls on a schedule in
production.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.core.redis_client import get_redis
from app.database.session import get_db
from app.models.job import Job
from app.models.rapid_apply import RapidApplyQueueEntry
from app.models.user import User
from app.schemas.rapid_apply import (
    CycleResultRead,
    DetectionResultRead,
    RapidApplyQueueEntryRead,
    RapidApplySettingsRead,
    RapidApplySettingsUpdate,
    RapidApplyStatsRead,
)
from app.services import rapid_apply_service
from app.services.profile_service import get_or_create_profile

router = APIRouter(prefix="/rapid-apply", tags=["rapid-apply"])


@router.get("/settings", response_model=RapidApplySettingsRead)
async def get_settings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_profile(db, user)
    return RapidApplySettingsRead(
        rapid_apply_enabled=profile.rapid_apply_enabled,
        min_match_score_to_apply=profile.min_match_score_to_apply,
    )


@router.put("/settings", response_model=RapidApplySettingsRead)
async def update_settings(
    payload: RapidApplySettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(db, user)
    if payload.rapid_apply_enabled is not None:
        profile.rapid_apply_enabled = payload.rapid_apply_enabled
    if payload.min_match_score_to_apply is not None:
        profile.min_match_score_to_apply = payload.min_match_score_to_apply
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return RapidApplySettingsRead(
        rapid_apply_enabled=profile.rapid_apply_enabled,
        min_match_score_to_apply=profile.min_match_score_to_apply,
    )


@router.post(
    "/run-cycle",
    response_model=CycleResultRead,
    dependencies=[Depends(rate_limit("rapid_apply_run_cycle", limit=60, window_seconds=60))],
)
async def run_cycle(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Manual trigger: runs one watch cycle right now for every
    Rapid-Apply-opted-in user (not just the caller) — mirrors exactly what
    the scheduled Celery task does, so this is a legitimate way to test or
    kick off the pipeline outside of waiting for the schedule."""
    redis_client = get_redis()
    result = await rapid_apply_service.run_cycle(db, redis_client)
    return CycleResultRead(
        detection=DetectionResultRead(**result.detection.__dict__),
        processed=result.processed,
        completed=result.completed,
        failed=result.failed,
    )


@router.get("/queue", response_model=list[RapidApplyQueueEntryRead])
async def list_queue(
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(RapidApplyQueueEntry)
        .options(selectinload(RapidApplyQueueEntry.job).selectinload(Job.company))
        .where(RapidApplyQueueEntry.user_id == user.id)
        .order_by(RapidApplyQueueEntry.priority.asc(), RapidApplyQueueEntry.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(RapidApplyQueueEntry.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/stats", response_model=RapidApplyStatsRead)
async def get_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    redis_client = get_redis()
    stats = await rapid_apply_service.get_stats(db, user, redis_client)
    return RapidApplyStatsRead(
        total_queued=stats.total_queued,
        queued=stats.queued,
        processing=stats.processing,
        completed=stats.completed,
        skipped=stats.skipped,
        failed=stats.failed,
        queue_depth_by_priority=stats.queue_depth_by_priority,
        latency=stats.latency.__dict__,
    )
