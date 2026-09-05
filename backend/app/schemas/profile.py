import uuid

from pydantic import BaseModel, ConfigDict


class EducationBase(BaseModel):
    degree: str | None = None
    university: str | None = None
    major: str | None = None
    minor: str | None = None
    graduation_year: int | None = None
    cgpa: float | None = None
    relevant_coursework: list[str] = []


class EducationCreate(EducationBase):
    pass


class EducationRead(EducationBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class ExperienceBase(BaseModel):
    company: str | None = None
    position: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    responsibilities: str | None = None
    achievements: str | None = None
    technologies: list[str] = []


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceRead(ExperienceBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class ProjectBase(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = []
    github_url: str | None = None
    demo_url: str | None = None
    achievements: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class CertificationBase(BaseModel):
    name: str | None = None
    issuer: str | None = None
    issued_date: str | None = None
    credential_url: str | None = None


class CertificationCreate(CertificationBase):
    pass


class CertificationRead(CertificationBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class SkillBase(BaseModel):
    name: str
    category: str = "other"


class SkillCreate(SkillBase):
    pass


class SkillRead(SkillBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class ProfileBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    job_types: list[str] = []
    work_modes: list[str] = []
    preferred_locations: list[str] = []
    min_salary: float | None = None
    experience_level: str | None = None
    preferred_roles: list[str] = []
    preferred_skills: list[str] = []


class ProfileUpdate(ProfileBase):
    pass


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    education: list[EducationRead] = []
    experience: list[ExperienceRead] = []
    projects: list[ProjectRead] = []
    certifications: list[CertificationRead] = []
    skills: list[SkillRead] = []
