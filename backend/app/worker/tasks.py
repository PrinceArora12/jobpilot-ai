"""
Celery task skeleton for the Rapid Apply watcher (spec section 57). Each
task opens its own AsyncSession/Redis client (Celery workers are separate
processes with no request-scoped dependencies) and delegates all real
logic to app.services.rapid_apply_service, which is what both this worker
and the manual `/api/rapid-apply/run-cycle` endpoint call — one behavior,
two triggers.
"""
import asyncio

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.database.session import AsyncSessionLocal, engine
from app.services import rapid_apply_service
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


async def _run_cycle_async() -> dict:
    # `engine` (and the pool backing AsyncSessionLocal) is created once at
    # worker process import time, but `run_rapid_apply_cycle` below spins up
    # a brand-new asyncio event loop on every single invocation via
    # `asyncio.run(...)` (celery beat calls it fresh every minute). asyncpg
    # connections are bound to the event loop that created them, so a pooled
    # connection left open past the end of this loop would get handed back
    # out on the *next* loop and blow up with "InterfaceError: cannot
    # perform operation: another operation is in progress". Disposing the
    # pool in `finally` forces every connection closed before this loop
    # goes away, so the next run starts clean. (Same root cause as
    # get_redis() not being @lru_cache'd — see app/core/redis_client.py.)
    try:
        async with AsyncSessionLocal() as db:
            redis_client = get_redis()
            result = await rapid_apply_service.run_cycle(db, redis_client)
            return {
                "jobs_detected": result.detection.jobs_detected,
                "evaluations": result.detection.evaluations,
                "queued": result.detection.queued,
                "skipped_ineligible": result.detection.skipped_ineligible,
                "skipped_low_score": result.detection.skipped_low_score,
                "processed": result.processed,
                "completed": result.completed,
                "failed": result.failed,
            }
    finally:
        await engine.dispose()


@celery_app.task(name="rapid_apply.run_cycle")
def run_rapid_apply_cycle() -> dict:
    """One watch-detect-match-queue-process cycle. Scheduled every minute
    via celery beat in production; callable directly (`.apply()` /
    `.delay()`) for manual runs, and executed synchronously when
    CELERY_TASK_ALWAYS_EAGER=True (tests, single-process dev)."""
    logger.info("rapid_apply_cycle_task_started")
    result = asyncio.run(_run_cycle_async())
    logger.info("rapid_apply_cycle_task_finished", **result)
    return result
