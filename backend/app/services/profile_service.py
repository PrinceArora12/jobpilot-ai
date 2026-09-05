"""
Profile CRUD service.

A tiny generic-child helper avoids repeating the same list/create/update/
delete logic five times (education, experience, projects, certifications,
skills) while keeping the API layer thin and type-explicit.
"""
import uuid
from typing import Generic, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import Profile
from app.models.user import User

ModelT = TypeVar("ModelT")
SchemaT = TypeVar("SchemaT", bound=BaseModel)


async def get_or_create_profile(db: AsyncSession, user: User) -> Profile:
    result = await db.execute(
        select(Profile)
        .options(
            selectinload(Profile.education),
            selectinload(Profile.experience),
            selectinload(Profile.projects),
            selectinload(Profile.certifications),
            selectinload(Profile.skills),
        )
        .where(Profile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id, first_name=user.first_name, last_name=user.last_name)
        db.add(profile)
        await db.commit()
        await db.refresh(profile, attribute_names=["education", "experience", "projects", "certifications", "skills"])
    return profile


class ChildResource(Generic[ModelT]):
    """CRUD helper for a Profile-owned child table (education, skills, ...)."""

    def __init__(self, model: type[ModelT]):
        self.model = model

    async def list_for_profile(self, db: AsyncSession, profile_id: uuid.UUID) -> list[ModelT]:
        result = await db.execute(select(self.model).where(self.model.profile_id == profile_id))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, profile_id: uuid.UUID, payload: BaseModel) -> ModelT:
        obj = self.model(profile_id=profile_id, **payload.model_dump())
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def get_owned_or_404(self, db: AsyncSession, profile_id: uuid.UUID, item_id: uuid.UUID) -> ModelT:
        result = await db.execute(
            select(self.model).where(self.model.id == item_id, self.model.profile_id == profile_id)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return obj

    async def update(
        self, db: AsyncSession, profile_id: uuid.UUID, item_id: uuid.UUID, payload: BaseModel
    ) -> ModelT:
        obj = await self.get_owned_or_404(db, profile_id, item_id)
        for field, value in payload.model_dump().items():
            setattr(obj, field, value)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, profile_id: uuid.UUID, item_id: uuid.UUID) -> None:
        obj = await self.get_owned_or_404(db, profile_id, item_id)
        await db.delete(obj)
        await db.commit()
