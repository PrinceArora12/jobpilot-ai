"""
Application tracking — spec sections 31/32/45. ApplicationEvent gives an
audit trail of every status change and note, which Phase 11's analytics
(response/interview/offer rates, application timing) reads from directly.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.database.types import GUID
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

APPLICATION_STATUSES = (
    "discovered",
    "matched",
    "saved",
    "preparing",
    "ready_for_review",
    "needs_manual_review",  # Phase 8: automation hit a failsafe (CAPTCHA/MFA/unmapped field) and stopped
    "submitted",
    "assessment",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
)

# Statuses that count as "a response happened" for analytics (Phase 11).
RESPONSE_STATUSES = {"assessment", "interview", "offer", "rejected"}


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("jobs.id"), nullable=False, index=True)
    resume_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("resumes.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="discovered", index=True)
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rapid Apply latency pipeline (spec section 58) — when a Rapid Apply
    # queue entry created this application, distinct from applied_at
    # (which tracks the human-meaningful "submitted" status transition).
    application_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    application_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job = relationship("Job")
    resume = relationship("Resume")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="ApplicationEvent.created_at"
    )


class ApplicationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "application_events"

    application_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("applications.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # status_changed | note | ...
    message: Mapped[str] = mapped_column(Text, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="events")
