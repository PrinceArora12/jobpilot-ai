"""
Rapid Apply queue — spec sections 57/58. Every entry is a durable Postgres
row (source of truth); a Redis-backed priority queue (app/services/
priority_queue.py) only holds the *ordering* of entry IDs so a worker can
pick the next one in O(1) without scanning the table. Losing Redis loses
nothing durable — it can always be rebuilt from rows with status="queued".

The timestamp columns implement the latency pipeline from spec section 58:
source_posted_at (on Job.posted_at) -> first_seen_at (Job) -> detected_at
(Job) -> normalized_at (Job) -> matched_at -> queued_at ->
application_started_at -> application_completed_at.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.database.types import GUID
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

QUEUE_STATUSES = ("queued", "processing", "completed", "skipped", "failed")


class RapidApplyQueueEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rapid_apply_queue"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_rapid_apply_queue_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("jobs.id"), nullable=False, index=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("applications.id"), nullable=True
    )

    match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0 (P0, highest) .. 3 (P3, lowest)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    application_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    application_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job = relationship("Job")
    application = relationship("Application")
