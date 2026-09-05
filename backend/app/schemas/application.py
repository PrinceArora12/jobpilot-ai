import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.application import APPLICATION_STATUSES
from app.schemas.job import JobRead


class ApplicationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    event_type: str
    message: str
    created_at: datetime


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    status: str = "discovered"

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in APPLICATION_STATUSES:
            raise ValueError(f"status must be one of {APPLICATION_STATUSES}")
        return v


class ApplicationUpdate(BaseModel):
    status: str | None = None
    resume_id: uuid.UUID | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str | None) -> str | None:
        if v is not None and v not in APPLICATION_STATUSES:
            raise ValueError(f"status must be one of {APPLICATION_STATUSES}")
        return v


class NoteCreate(BaseModel):
    message: str


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    job: JobRead
    resume_id: uuid.UUID | None
    status: str
    match_score: int | None
    notes: str | None
    discovered_at: datetime
    applied_at: datetime | None
    events: list[ApplicationEventRead]
    created_at: datetime
