"""
Backing store for the mock job source (spec section 56): lets tests and
demos simulate "a company publishes a new job" without touching any real
job board, so the whole detect -> match -> apply pipeline can be exercised
end-to-end. MockJobSource (app/connectors/mock_source.py) drains this table.
"""
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.database.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MockJobPosting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mock_job_postings"

    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    source_posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
