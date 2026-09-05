import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MockJobCreate(BaseModel):
    """Raw, provider-shaped payload — same shape any adapter would produce
    before normalization. Mirrors spec section 56's mock job board."""

    title: str
    company: str
    location: str | None = None
    remote: bool = False
    employment_type: str | None = None  # internship/full_time/part_time/contract
    experience_level: str | None = None
    salary: str | None = None
    description: str = ""
    requirements: list[str] = []
    skills: list[str] = []
    url: str | None = None
    external_id: str | None = None
    posted_at: datetime | None = None
    deadline: datetime | None = None
    # Phase 8: which mock application-form the Rapid Apply automator will
    # see for this job — lets tests (and demos) exercise every failsafe
    # path deliberately. Defaults to a form automation can complete cleanly.
    form_variant: str = "standard"  # standard | captcha | mfa | unknown_field


class MockJobPostingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_posted_at: datetime
    consumed_at: datetime | None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    is_blocked: bool
    is_favorite: bool


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: str
    source: str
    title: str
    company: CompanyRead
    location: str | None
    remote: bool
    employment_type: str | None
    experience_level: str | None
    salary: str | None
    description: str | None
    requirements: list[str]
    skills: list[str]
    url: str
    posted_at: datetime | None
    deadline: datetime | None
    first_seen_at: datetime
    automation_variant: str


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int


class JobSearchParams(BaseModel):
    q: str | None = None
    employment_type: str | None = None
    experience_level: str | None = None
    remote: bool | None = None
    location: str | None = None
    source: str | None = None
    skill: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
