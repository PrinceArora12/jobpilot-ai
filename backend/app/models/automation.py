"""
Automation control — spec sections 60-62. One AutomationRule row per user
(created lazily, like Profile) governs Rapid Apply's global on/off switch
plus hard caps that apply *no matter how good a match looks* — a perfect
score never overrides a rate limit or a blocklist entry, which is the
whole point of giving the user a kill switch and limits they can trust.

Notification is the in-app feed spec section 62 asks for: every automated
submission, every fallback to manual review, and every moment automation
pauses itself (rate limit reached, user hit Stop) writes one row here.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.database.types import GUID, StringArray
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

AUTOMATION_STATES = ("running", "paused", "stopped")


class AutomationRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "automation_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), unique=True, nullable=False)

    # "running" lets Rapid Apply operate (still gated by Profile.rapid_apply_enabled,
    # the Phase 7 feature toggle); "paused" is a resumable hold; "stopped" is the
    # deliberate global kill switch — spec section 62's "Global STOP button".
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="running")

    # None = unlimited. Enforced regardless of match score or eligibility.
    max_applications_per_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_applications_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_applications_per_company: Mapped[int | None] = mapped_column(Integer, nullable=True)

    blocked_sources: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    blocked_companies: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    blocked_keywords: Mapped[list[str]] = mapped_column(StringArray(), default=list)


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("applications.id"), nullable=True
    )

    application = relationship("Application")
