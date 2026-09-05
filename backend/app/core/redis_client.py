"""
Async Redis client factory, built from settings.REDIS_URL. Used by the
Rapid Apply priority queue (app/services/priority_queue.py) and, in later
phases, rate limiting (Phase 12) and notifications (Phase 10).

Deliberately NOT cached as a process-wide singleton: redis-py's async
client ties its connection pool to the event loop it was first used on,
and both pytest (a fresh event loop per test function) and a real ASGI
server (uvicorn workers) can end up running this code across more than
one loop. `redis.from_url` is cheap and lazy (no socket is opened until
the first command), so a fresh client per call is the simplest way to
never hand a coroutine a pool bound to a dead loop.
"""
import redis.asyncio as redis

from app.core.config import settings


def get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
