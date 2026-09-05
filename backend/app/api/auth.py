"""
Authentication endpoints: register, login, me.

Passwords are hashed with bcrypt (app.core.security) before storage.
JobPilot AI never stores plaintext passwords, and this module has nothing
to do with any external job portal's credentials (spec section 6/51).
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
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
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)

VERIFICATION_TOKEN_TTL_HOURS = 24


class MessageResponse(BaseModel):
    message: str


def _issue_verification_token(user: User) -> str:
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(
        hours=VERIFICATION_TOKEN_TTL_HOURS
    )
    return token


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
    verification_token = _issue_verification_token(user)
    db.add(user)
    await db.flush()
    await log_action(db, "auth.register", user_id=user.id, ip_address=_client_ip(request))
    await db.commit()
    await db.refresh(user)

    logger.info("user_registered", user_id=str(user.id), email=user.email)
    # Best-effort: send_verification_email never raises (see email_service),
    # so a misconfigured/unreachable SMTP server can't block registration.
    send_verification_email(user.email, verification_token)

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


@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already-used verification link")

    expires_at = user.verification_token_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link has expired. Request a new one from the app.",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    await log_action(db, "auth.email_verified", user_id=user.id)
    await db.commit()

    logger.info("user_email_verified", user_id=str(user.id), email=user.email)
    return MessageResponse(message="Email verified successfully.")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("auth_resend_verification", limit=5, window_seconds=300))],
)
async def resend_verification(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if current_user.is_verified:
        return MessageResponse(message="Your email is already verified.")

    token = _issue_verification_token(current_user)
    await db.commit()
    send_verification_email(current_user.email, token)

    logger.info("verification_email_resent", user_id=str(current_user.id))
    return MessageResponse(message="Verification email sent. Check your inbox.")
