"""Analytics API — spec section 11 (Phase 11)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryRead,
    FunnelRead,
    ResumePerformanceRead,
    TimelinePointRead,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryRead)
async def summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_summary(db, user.id)


@router.get("/funnel", response_model=FunnelRead)
async def funnel(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_funnel(db, user.id)


@router.get("/resume-performance", response_model=list[ResumePerformanceRead])
async def resume_performance(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_resume_performance(db, user.id)


@router.get("/timeline", response_model=list[TimelinePointRead])
async def timeline(
    days: int = Query(default=30, ge=1, le=180),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await analytics_service.get_timeline(db, user.id, days=days)
