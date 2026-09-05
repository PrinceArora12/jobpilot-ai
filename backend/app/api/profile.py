"""
Profile API — personal info, job preferences, and child collections
(education, experience, projects, certifications, skills). Spec sections
7-8.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.profile import Certification, Education, Experience, Project, Skill
from app.models.user import User
from app.schemas.profile import (
    CertificationCreate,
    CertificationRead,
    EducationCreate,
    EducationRead,
    ExperienceCreate,
    ExperienceRead,
    ProfileRead,
    ProfileUpdate,
    ProjectCreate,
    ProjectRead,
    SkillCreate,
    SkillRead,
)
from app.services.profile_service import ChildResource, get_or_create_profile

router = APIRouter(prefix="/profile", tags=["profile"])

education_crud = ChildResource(Education)
experience_crud = ChildResource(Experience)
project_crud = ChildResource(Project)
certification_crud = ChildResource(Certification)
skill_crud = ChildResource(Skill)


@router.get("", response_model=ProfileRead)
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_or_create_profile(db, user)


@router.put("", response_model=ProfileRead)
async def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(db, user)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    await db.commit()
    return await get_or_create_profile(db, user)


def _child_router(
    path: str,
    crud: ChildResource,
    create_schema: type,
    read_schema: type,
):
    sub = APIRouter(prefix=f"/{path}", tags=["profile"])

    @sub.get("", response_model=list[read_schema])
    async def list_items(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        profile = await get_or_create_profile(db, user)
        return await crud.list_for_profile(db, profile.id)

    @sub.post("", response_model=read_schema, status_code=201)
    async def create_item(
        payload: create_schema,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        profile = await get_or_create_profile(db, user)
        return await crud.create(db, profile.id, payload)

    @sub.put("/{item_id}", response_model=read_schema)
    async def update_item(
        item_id: uuid.UUID,
        payload: create_schema,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        profile = await get_or_create_profile(db, user)
        return await crud.update(db, profile.id, item_id, payload)

    @sub.delete("/{item_id}", status_code=204)
    async def delete_item(
        item_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        profile = await get_or_create_profile(db, user)
        await crud.delete(db, profile.id, item_id)

    return sub


router.include_router(_child_router("education", education_crud, EducationCreate, EducationRead))
router.include_router(_child_router("experience", experience_crud, ExperienceCreate, ExperienceRead))
router.include_router(_child_router("projects", project_crud, ProjectCreate, ProjectRead))
router.include_router(
    _child_router("certifications", certification_crud, CertificationCreate, CertificationRead)
)
router.include_router(_child_router("skills", skill_crud, SkillCreate, SkillRead))
