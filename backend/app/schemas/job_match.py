import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.job import JobRead


class JobMatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    job: JobRead
    overall_score: int
    skills_score: int
    education_score: int
    experience_score: int
    location_score: int
    role_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: str | None
    is_eligible: bool
    eligibility_reasons: list[str]
    created_at: datetime
