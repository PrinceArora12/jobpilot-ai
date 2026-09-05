"""
Profile models — spec section 7/8.

One Profile per User (personal info + job preferences), with Education,
Experience, Project, Certification, and Skill as child collections.
"""
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.database.types import GUID, StringArray
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), unique=True, nullable=False)

    # Personal information
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    github_url: Mapped[str | None] = mapped_column(String(255))
    portfolio_url: Mapped[str | None] = mapped_column(String(255))

    # Job preferences (spec section 8)
    job_types: Mapped[list[str]] = mapped_column(StringArray(), default=list)  # internship/full_time/part_time/contract
    work_modes: Mapped[list[str]] = mapped_column(StringArray(), default=list)  # remote/hybrid/on_site
    preferred_locations: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    min_salary: Mapped[float | None] = mapped_column(Float)
    experience_level: Mapped[str | None] = mapped_column(String(50))  # fresher/entry_level/0-1/1-2/...
    preferred_roles: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(StringArray(), default=list)

    # Rapid Apply opt-in (spec section 57/60) — the watcher only screens
    # jobs against users who have explicitly turned this on; Phase 10 adds
    # the finer-grained per-hour/day/source/company limits on top of it.
    rapid_apply_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_match_score_to_apply: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    user = relationship("User", backref="profile", uselist=False)
    education: Mapped[list["Education"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="Education.graduation_year.desc()"
    )
    experience: Mapped[list["Experience"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    skills: Mapped[list["Skill"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class Education(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "education"

    profile_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("profiles.id"), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(150))
    university: Mapped[str | None] = mapped_column(String(200))
    major: Mapped[str | None] = mapped_column(String(150))
    minor: Mapped[str | None] = mapped_column(String(150))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    cgpa: Mapped[float | None] = mapped_column(Float)
    relevant_coursework: Mapped[list[str]] = mapped_column(StringArray(), default=list)

    profile: Mapped["Profile"] = relationship(back_populates="education")


class Experience(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "experience"

    profile_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("profiles.id"), nullable=False)
    company: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[str | None] = mapped_column(String(20))  # ISO YYYY-MM
    end_date: Mapped[str | None] = mapped_column(String(20))  # null/"" = current
    responsibilities: Mapped[str | None] = mapped_column(Text)
    achievements: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list[str]] = mapped_column(StringArray(), default=list)

    profile: Mapped["Profile"] = relationship(back_populates="experience")


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    profile_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("profiles.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    github_url: Mapped[str | None] = mapped_column(String(255))
    demo_url: Mapped[str | None] = mapped_column(String(255))
    achievements: Mapped[str | None] = mapped_column(Text)

    profile: Mapped["Profile"] = relationship(back_populates="projects")


class Certification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "certifications"

    profile_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("profiles.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    issuer: Mapped[str | None] = mapped_column(String(200))
    issued_date: Mapped[str | None] = mapped_column(String(20))
    credential_url: Mapped[str | None] = mapped_column(String(255))

    profile: Mapped["Profile"] = relationship(back_populates="certifications")


SKILL_CATEGORIES = (
    "programming_languages",
    "frameworks",
    "databases",
    "cloud",
    "ai_ml",
    "data_tools",
    "devops",
    "other",
    "soft_skills",
)


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    profile_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("profiles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")

    profile: Mapped["Profile"] = relationship(back_populates="skills")
