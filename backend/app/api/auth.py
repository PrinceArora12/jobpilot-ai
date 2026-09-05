"""
Authentication endpoints: register, login, me.

Passwords are hashed with bcrypt (app.core.security) before storage.
JobPilot AI never stores plaintext passwords, and this module has nothing
to do with any external job portal's credentials (spec section 6/51).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import Token, TokenWithUser
from app.schemas.user import UserLogin, UserRead, UserRegister
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/register",
    response_model=TokenWithUser,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth_register", limit=10, window_seconds=300))],
)
async def register(payload: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(user)
    await db.flush()
    await log_action(db, "auth.register", user_id=user.id, ip_address=_client_ip(request))
    await db.commit()
    await db.refresh(user)

    logger.info("user_registered", user_id=str(user.id), email=user.email)

    token = create_access_token(subject=str(user.id))
    return TokenWithUser(access_token=token, user=UserRead.model_validate(user))


@router.post(
    "/login",
    response_model=TokenWithUser,
    dependencies=[Depends(rate_limit("auth_login", limit=20, window_seconds=300))],
)
async def login(payload: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        # Never attribute a failed attempt to a user_id derived from
        # unverified input — if no account matched, this is anonymous.
        await log_action(
            db,
            "auth.login_failed",
            user_id=user.id if user else None,
            detail=f"email={payload.email}",
            ip_address=_client_ip(request),
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        await log_action(
            db, "auth.login_blocked_inactive", user_id=user.id, ip_address=_client_ip(request)
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    await log_action(db, "auth.login_success", user_id=user.id, ip_address=_client_ip(request))
    await db.commit()

    logger.info("user_logged_in", user_id=str(user.id), email=user.email)

    token = create_access_token(subject=str(user.id))
    return TokenWithUser(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)):
    return UserRead.model_validate(current_user)
