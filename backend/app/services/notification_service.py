"""In-app notification feed — spec section 62."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import Notification


async def notify(
    db: AsyncSession,
    user_id,
    type: str,
    title: str,
    message: str,
    application_id=None,
) -> Notification:
    notification = Notification(
        user_id=user_id, type=type, title=title, message=message, application_id=application_id
    )
    db.add(notification)
    await db.flush()
    return notification


async def list_notifications(
    db: AsyncSession, user_id, unread_only: bool = False, limit: int = 50
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def unread_count(db: AsyncSession, user_id) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )


async def mark_read(db: AsyncSession, user_id, notification_id: uuid.UUID) -> Notification | None:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        return None
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_all_read(db: AsyncSession, user_id) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount or 0
