import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.database.types import GUID, StringArray
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class JobMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("jobs.id"), nullable=False, index=True)

    overall_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    skills_score: Mapped[int] = mapped_column(Integer, nullable=False)
    education_score: Mapped[int] = mapped_column(Integer, nullable=False)
    experience_score: Mapped[int] = mapped_column(Integer, nullable=False)
    location_score: Mapped[int] = mapped_column(Integer, nullable=False)
    role_score: Mapped[int] = mapped_column(Integer, nullable=False)

    matched_skills: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    missing_skills: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    explanation: Mapped[str | None] = mapped_column(Text)
    is_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    eligibility_reasons: Mapped[list[str]] = mapped_column(StringArray(), default=list)

    job = relationship("Job")
