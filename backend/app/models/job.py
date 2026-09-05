"""
Job engine models — spec sections 11/12/45.

Design note: the spec lists `job_skills` as its own join table. This build
uses a `skills` array column on `Job` instead (StringArray, cross-dialect —
see app/database/types.py) to keep the schema simpler while still
satisfying every query the spec actually asks for (skills matching,
missing-skills diffing). Documented here rather than silently deviating.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.database.types import GUID, StringArray
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    careers_url: Mapped[str | None] = mapped_column(String(500))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),)

    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(255))
    remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(50))  # internship/full_time/part_time/contract
    experience_level: Mapped[str | None] = mapped_column(String(50))
    salary: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    skills: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Rapid Apply latency pipeline (spec section 58). `posted_at` above
    # doubles as source_posted_at; these two are stamped by the Phase 7
    # watcher the moment ingestion (detection + normalization, which are
    # synchronous in this build) finishes for a newly-created job.
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Phase 8: which mock application-form variant this job links to
    # (standard/captcha/mfa/unknown_field — see app/api/mock_forms.py).
    # Only ever meaningful for source="mock" jobs: browser automation in
    # this build NEVER runs against a real job portal (spec section 6/51),
    # so a real-source job simply has no automatable form at all.
    automation_variant: Mapped[str] = mapped_column(String(30), default="standard", nullable=False)

    company: Mapped["Company"] = relationship(back_populates="jobs")
