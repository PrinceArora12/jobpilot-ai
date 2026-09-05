"""
AI Application Assistant API — spec sections 20-24. Two independent
capabilities, both grounded-or-refuse:

  - Free-text screening question answering (app/agents/application_assistant.py)
  - Resume tailoring, previewed then explicitly applied (app/services/resume_tailor_service.py)

Neither endpoint calls an LLM to invent facts; both only ever reformat or
reorder data that's already on the user's own profile/resume.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.application_assistant import answer_question
from app.ai.factory import get_ai_provider
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.application import Application
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.resume import Resume
from app.models.user import User
from app.schemas.assistant import (
    AssistantAnswerResponse,
    AssistantQuestionRequest,
    TailorApplyRequest,
    TailorPreviewRequest,
    TailorPreviewResponse,
)
from app.schemas.resume import ResumeRead
from app.services.profile_service import get_or_create_profile
from app.services.resume_tailor_service import TailoringValidationError, apply_tailoring, preview_tailoring

router = APIRouter(prefix="/assistant", tags=["assistant"])


async def _get_owned_resume(db: AsyncSession, user: User, resume_id) -> Resume:
    result = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


async def _get_owned_job(db: AsyncSession, job_id) -> Job:
    result = await db.execute(select(Job).options(selectinload(Job.company)).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/answer", response_model=AssistantAnswerResponse)
async def answer(
    payload: AssistantQuestionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app_result = await db.execute(
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.company))
        .where(Application.id == payload.application_id, Application.user_id == user.id)
    )
    application = app_result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    profile = await get_or_create_profile(db, user)

    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == user.id, Resume.is_primary.is_(True))
    )
    resume = resume_result.scalar_one_or_none()

    match_result = await db.execute(
        select(JobMatch.matched_skills).where(JobMatch.user_id == user.id, JobMatch.job_id == application.job_id)
    )
    matched_skills = match_result.scalar_one_or_none() or []

    ai = get_ai_provider()
    result = await answer_question(payload.question, profile, resume, application.job, matched_skills, ai)
    return AssistantAnswerResponse(
        status=result.status,
        answer=result.answer,
        confidence=result.confidence,
        source=result.source,
        reason=result.reason,
    )


@router.post("/tailor-resume/preview", response_model=TailorPreviewResponse)
async def tailor_preview(
    payload: TailorPreviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _get_owned_resume(db, user, payload.resume_id)
    job = await _get_owned_job(db, payload.job_id)
    preview = preview_tailoring(resume, job)
    return TailorPreviewResponse(
        original_order=preview.original_order,
        suggested_order=preview.suggested_order,
        matched_keywords=preview.matched_keywords,
        changed=preview.changed,
    )


@router.post("/tailor-resume/apply", response_model=ResumeRead)
async def tailor_apply(
    payload: TailorApplyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _get_owned_resume(db, user, payload.resume_id)
    try:
        apply_tailoring(resume, payload.skill_order)
    except TailoringValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume
