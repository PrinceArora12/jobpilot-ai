"""
Redis-backed rate limiting — spec section 12 (production hardening). A
simple fixed-window counter (INCR, with EXPIRE set on the first hit of
each window) keyed by client IP plus a route-specific bucket name. Chosen
over a token bucket for simplicity, and because Redis already backs the
Rapid Apply queue (app/services/priority_queue.py) — no new infrastructure
is introduced just for this.

Fails OPEN: if Redis is unreachable, requests are let through rather than
locking every user out because of an unrelated infra hiccup. A rate
limiter's job is to blunt abuse, not to become a second point of failure
for every request in the app.
"""
from fastapi import HTTPException, Request, status

from app.core.logging import get_logger
from app.core.redis_client import get_redis

logger = get_logger(__name__)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, limit: int, window_seconds: int):
    """FastAPI dependency factory. Use as:

        @router.post("/login", dependencies=[Depends(rate_limit("auth_login", 10, 300))])

    `bucket` namespaces the counter per route/purpose so different
    endpoints don't share a budget; `limit` requests are allowed per
    `window_seconds` per client IP.
    """

    async def dependency(request: Request) -> None:
        key = f"ratelimit:{bucket}:{_client_ip(request)}"
        try:
            redis_client = get_redis()
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, window_seconds)
        except Exception:  # noqa: BLE001 — Redis being down must never block real traffic
            logger.warning("rate_limit_check_failed", bucket=bucket)
            return

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests — please wait a bit and try again.",
            )

    return dependency
