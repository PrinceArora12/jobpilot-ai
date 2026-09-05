"""
Account-wide audit log — spec section 52. Every security- and
data-relevant action a user (or the system acting on their behalf, e.g.
Rapid Apply) takes is recorded here: auth events, application status
changes, automation rule/state changes, and resume management. This is
intentionally append-only from the API's point of view — there is no
update or delete endpoint, only create and list.
"""
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.database.types import GUID
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    # Nullable: a failed login attempt against an email that doesn't exist
    # has no user to attribute it to, but is still worth recording.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
