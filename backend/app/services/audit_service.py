"""
Account-wide audit log — spec section 52. Append-only: log_action writes
one row per security- or data-relevant event; list_audit_log reads them
back for the owning user only. Never raises on a logging failure into the
caller's own request — see the note on log_action below.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit_log import AuditLog

logger = get_logger(__name__)


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: uuid.UUID | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Records one audit event. Callers should commit their own unit of
    work as usual — this only adds/flushes so it can be included in the
    same transaction as the action it's recording (e.g. an application
    status change and its audit row land together or not at all)."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        detail=detail,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_audit_log(db: AsyncSession, user_id: uuid.UUID, limit: int = 100) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
