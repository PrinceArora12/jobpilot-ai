"""
Resume management API — upload, list, view, edit extracted data, delete,
set-primary, multiple resumes per user (spec section 9-10).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.database.session import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeRead, ResumeUpdate
from app.services.audit_service import log_action
from app.services.resume_parser import extract_text, parse_resume
from app.services.storage import delete_file, resume_storage_path

router = APIRouter(prefix="/resumes", tags=["resumes"])
logger = get_logger(__name__)

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


@router.get("", response_model=list[ResumeRead])
async def list_resumes(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile,
    label: str = "Resume",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_type = ALLOWED_TYPES.get(file.content_type or "")
    if file_type is None and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
        file_type = ext if ext in {"pdf", "docx"} else None
    if file_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX resumes are supported.",
        )

    resume_id = uuid.uuid4()
    dest = resume_storage_path(user.id, resume_id, file_type)
    contents = await file.read()
    dest.write_bytes(contents)

    try:
        raw_text = extract_text(dest, file_type)
        parsed_data = parse_resume(raw_text)
    except Exception:  # noqa: BLE001 — a bad upload must not 500 the request
        logger.warning("resume_parse_failed", filename=file.filename)
        raw_text, parsed_data = None, None

    existing_count = await db.scalar(
        select(Resume.id).where(Resume.user_id == user.id).limit(1)
    )

    resume = Resume(
        id=resume_id,
        user_id=user.id,
        label=label,
        original_filename=file.filename or f"resume.{file_type}",
        file_path=str(dest),
        file_type=file_type,
        is_primary=existing_count is None,  # first upload becomes primary automatically
        raw_text=raw_text,
        parsed_data=parsed_data,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    logger.info("resume_uploaded", user_id=str(user.id), resume_id=str(resume.id), file_type=file_type)
    return resume


async def _get_owned_resume(db: AsyncSession, user: User, resume_id: uuid.UUID) -> Resume:
    result = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


@router.get("/{resume_id}", response_model=ResumeRead)
async def get_resume(
    resume_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _get_owned_resume(db, user, resume_id)


@router.put("/{resume_id}", response_model=ResumeRead)
async def update_resume(
    resume_id: uuid.UUID,
    payload: ResumeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _get_owned_resume(db, user, resume_id)

    if payload.label is not None:
        resume.label = payload.label
    if payload.parsed_data is not None:
        resume.parsed_data = payload.parsed_data
    if payload.is_primary:
        await db.execute(
            update(Resume).where(Resume.user_id == user.id, Resume.id != resume.id).values(is_primary=False)
        )
        resume.is_primary = True
    elif payload.is_primary is False:
        resume.is_primary = False

    await db.commit()
    await db.refresh(resume)
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    resume = await _get_owned_resume(db, user, resume_id)
    delete_file(resume.file_path)
    await db.delete(resume)
    await log_action(db, "resume.deleted", user_id=user.id, detail=f"resume_id={resume_id} label={resume.label}")
    await db.commit()
