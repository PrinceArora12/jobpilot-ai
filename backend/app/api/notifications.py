"""In-app notification feed API — spec section 62."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.automation import NotificationRead
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.list_notifications(db, user.id, unread_only=unread_only)


@router.get("/unread-count")
async def get_unread_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"unread_count": await notification_service.unread_count(db, user.id)}


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def read_one(
    notification_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    notification = await notification_service.mark_read(db, user.id, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/read-all")
async def read_all(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    count = await notification_service.mark_all_read(db, user.id)
    return {"marked_read": count}
