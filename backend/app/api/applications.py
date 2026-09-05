"""
Application tracker API — spec sections 31/32. Every status change and
note is recorded as an ApplicationEvent so the timeline is auditable
(spec section 52's audit log requirement, applied to applications
specifically; Phase 12 adds the account-wide audit log).
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.database.session import get_db
from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    NoteCreate,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/applications", tags=["applications"])
logger = get_logger(__name__)


def _with_relations(stmt):
    return stmt.options(
        selectinload(Application.job).selectinload(Job.company),
        selectinload(Application.events),
    )


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Application).where(Application.user_id == user.id, Application.job_id == payload.job_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already tracking this job")

    job_result = await db.execute(select(Job).where(Job.id == payload.job_id))
    if job_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    match_result = await db.execute(
        select(JobMatch.overall_score).where(JobMatch.user_id == user.id, JobMatch.job_id == payload.job_id)
    )
    match_score = match_result.scalar_one_or_none()

    application = Application(
        user_id=user.id,
        job_id=payload.job_id,
        resume_id=payload.resume_id,
        status=payload.status,
        match_score=match_score,
        discovered_at=datetime.now(timezone.utc),
    )
    db.add(application)
    await db.flush()
    db.add(
        ApplicationEvent(
            application_id=application.id,
            event_type="status_changed",
            message=f"Application created with status '{payload.status}'",
        )
    )
    await db.commit()

    logger.info("application_created", application_id=str(application.id), job_id=str(payload.job_id))

    result = await db.execute(_with_relations(select(Application)).where(Application.id == application.id))
    return result.scalar_one()


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = _with_relations(select(Application)).where(Application.user_id == user.id)
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    stmt = stmt.order_by(Application.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_owned_application(db: AsyncSession, user: User, application_id: uuid.UUID) -> Application:
    result = await db.execute(
        _with_relations(select(Application)).where(
            Application.id == application_id, Application.user_id == user.id
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _get_owned_application(db, user, application_id)


@router.put("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await _get_owned_application(db, user, application_id)

    if payload.status is not None and payload.status != application.status:
        old_status = application.status
        application.events.append(
            ApplicationEvent(
                event_type="status_changed",
                message=f"Status changed from '{application.status}' to '{payload.status}'",
            )
        )
        application.status = payload.status
        if payload.status == "submitted" and application.applied_at is None:
            application.applied_at = datetime.now(timezone.utc)
        await log_action(
            db,
            "application.status_changed",
            user_id=user.id,
            detail=f"application_id={application.id} {old_status} -> {payload.status}",
            ip_address=request.client.host if request.client else None,
        )

    if payload.resume_id is not None:
        application.resume_id = payload.resume_id
    if payload.notes is not None:
        application.notes = payload.notes

    await db.commit()
    return await _get_owned_application(db, user, application_id)


@router.post("/{application_id}/notes", response_model=ApplicationRead)
async def add_note(
    application_id: uuid.UUID,
    payload: NoteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await _get_owned_application(db, user, application_id)
    application.events.append(ApplicationEvent(event_type="note", message=payload.message))
    await db.commit()
    return await _get_owned_application(db, user, application_id)


@router.post("/{application_id}/auto-submit", response_model=ApplicationRead)
async def auto_submit_application(
    application_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Manually (re-)runs Phase 8's browser automation for one
    application — useful both for testing the pipeline directly and for
    retrying an application stuck in "needs_manual_review" after the user
    has fixed whatever the automator couldn't handle (e.g. added a resume,
    filled in a phone number)."""
    from app.services.automation_service import attempt_submission

    application = await _get_owned_application(db, user, application_id)
    job_result = await db.execute(select(Job).where(Job.id == application.job_id))
    job = job_result.scalar_one()

    await attempt_submission(db, application, job, user)
    return await _get_owned_application(db, user, application_id)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    application = await _get_owned_application(db, user, application_id)
    await db.delete(application)
    await db.commit()
