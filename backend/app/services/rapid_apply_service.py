"""
Rapid Apply engine — spec sections 57/58. Orchestrates:

  watcher (drain mock source) -> ingest (normalize+dedup, Phase 4)
    -> fast eligibility filter (Phase 5) -> AI match scoring (Phase 5)
    -> priority queue (Redis, P0-P3) -> queue processing

Processing a queue entry creates the Application record, then hands it to
Phase 8's browser automation (app/services/automation_service.py). A
queue entry's own status ("queued"/"processing"/"completed"/"failed")
only describes whether *the queue finished processing it* — the resulting
Application's status ("submitted" vs "needs_manual_review") is the
separate, honest answer to "did we actually apply anywhere."

Every stage stamps a timestamp so latency can be measured end-to-end
(spec section 58): source_posted_at -> first_seen_at -> detected_at ->
normalized_at -> matched_at -> queued_at -> application_started_at ->
application_completed_at.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.factory import get_ai_provider
from app.connectors.mock_source import MockJobSource
from app.core.logging import get_logger
from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.profile import Profile
from app.models.rapid_apply import RapidApplyQueueEntry
from app.models.user import User
from app.services.automation_rules_service import get_or_create_rule, screening_block_reason
from app.services.eligibility import check_eligibility
from app.services.job_ingestion import ingest_job
from app.services.match_service import compute_and_store_match
from app.services.notification_service import notify
from app.services.priority_queue import RedisPriorityQueue, score_to_priority

logger = get_logger(__name__)

#: Below this overall match score, a job is not worth auto-queuing at all
#: (still visible to the user manually via normal job search/matching).
DEFAULT_MIN_QUEUE_SCORE = 50

#: Safety cap so a single API-triggered cycle can't loop forever.
MAX_PROCESS_PER_CYCLE = 200


@dataclass
class DetectionResult:
    jobs_detected: int = 0
    evaluations: int = 0
    queued: int = 0
    skipped_ineligible: int = 0
    skipped_low_score: int = 0
    already_queued: int = 0
    skipped_by_automation_rules: int = 0


@dataclass
class CycleResult:
    detection: DetectionResult = field(default_factory=DetectionResult)
    processed: int = 0
    completed: int = 0
    failed: int = 0


def _queue_for(redis_client: Redis, namespace: str = "default") -> RedisPriorityQueue:
    return RedisPriorityQueue(redis_client, namespace=namespace)


async def _rapid_apply_users(db: AsyncSession) -> list[tuple[User, Profile]]:
    result = await db.execute(
        select(User, Profile)
        .join(Profile, Profile.user_id == User.id)
        .where(Profile.rapid_apply_enabled.is_(True), User.is_active.is_(True))
    )
    return [(row[0], row[1]) for row in result.all()]


async def detect_and_enqueue(db: AsyncSession, redis_client: Redis) -> DetectionResult:
    """Drains the mock source, ingests any new jobs, and screens each one
    against every Rapid-Apply-opted-in user's profile."""
    result = DetectionResult()
    queue = _queue_for(redis_client)

    raw_jobs = await MockJobSource(db).fetch_jobs()
    newly_detected: list[Job] = []
    for raw in raw_jobs:
        job, created = await ingest_job(db, raw, source="mock")
        if created:
            now = datetime.now(timezone.utc)
            job.detected_at = now
            # Normalization happens synchronously inside ingest_job above,
            # so it completes at effectively the same instant it's detected.
            job.normalized_at = now
            db.add(job)
            newly_detected.append(job)
    if newly_detected:
        await db.commit()
        for job in newly_detected:
            await db.refresh(job)
    result.jobs_detected = len(newly_detected)

    if not newly_detected:
        return result

    users = await _rapid_apply_users(db)
    ai = get_ai_provider()
    rate_limit_notified: set = set()

    for job in newly_detected:
        # job.company is needed by eligibility checks; refresh with it loaded.
        job_result = await db.execute(
            select(Job).options(selectinload(Job.company)).where(Job.id == job.id)
        )
        job = job_result.scalar_one()

        for user, profile in users:
            rule = await get_or_create_rule(db, user)
            block_reason = await screening_block_reason(db, rule, user.id, job)
            if block_reason is not None:
                result.skipped_by_automation_rules += 1
                if block_reason.startswith("rate_limit:") and user.id not in rate_limit_notified:
                    rate_limit_notified.add(user.id)
                    await notify(
                        db,
                        user.id,
                        type="rate_limit_reached",
                        title="Rapid Apply paused for now",
                        message=f"A configured limit ({block_reason.split(':', 1)[1]}) stopped new applications this cycle.",
                    )
                    await db.commit()
                continue

            result.evaluations += 1

            eligibility = check_eligibility(profile, job)
            if not eligibility.passed:
                result.skipped_ineligible += 1
                continue

            match = await compute_and_store_match(db, user, job, ai)
            matched_at = datetime.now(timezone.utc)

            min_score = profile.min_match_score_to_apply or DEFAULT_MIN_QUEUE_SCORE
            if match.overall_score < min_score:
                result.skipped_low_score += 1
                continue

            existing = await db.execute(
                select(RapidApplyQueueEntry).where(
                    RapidApplyQueueEntry.user_id == user.id, RapidApplyQueueEntry.job_id == job.id
                )
            )
            if existing.scalar_one_or_none() is not None:
                result.already_queued += 1
                continue

            priority = score_to_priority(match.overall_score)
            queued_at = datetime.now(timezone.utc)
            entry = RapidApplyQueueEntry(
                user_id=user.id,
                job_id=job.id,
                match_score=match.overall_score,
                priority=priority,
                status="queued",
                source_posted_at=job.posted_at,
                first_seen_at=job.first_seen_at,
                detected_at=job.detected_at,
                normalized_at=job.normalized_at,
                matched_at=matched_at,
                queued_at=queued_at,
            )
            db.add(entry)
            await db.flush()
            await queue.enqueue(str(entry.id), priority)
            result.queued += 1
            logger.info(
                "rapid_apply_queued",
                entry_id=str(entry.id),
                job_id=str(job.id),
                user_id=str(user.id),
                priority=priority,
                score=match.overall_score,
            )

    await db.commit()
    return result


async def process_next(db: AsyncSession, redis_client: Redis) -> RapidApplyQueueEntry | None:
    """Pops and processes exactly one queue entry, or returns None if the
    queue is empty. Creates the Application, then hands it straight to
    Phase 8's browser automation (app/services/automation_service.py):
    it ends up "submitted" when automation completes cleanly, or
    "needs_manual_review" the moment any failsafe (CAPTCHA/MFA/unmapped
    field/non-mock source) trips — never silently stuck, never guessed."""
    # Imported here rather than at module scope solely to keep this
    # module importable without pulling in Playwright for callers (like
    # the plain detection/stats tests) that never touch automation.
    from app.services.automation_service import attempt_submission

    queue = _queue_for(redis_client)
    entry_id = await queue.dequeue()
    if entry_id is None:
        return None

    entry = await db.get(RapidApplyQueueEntry, uuid.UUID(entry_id))
    if entry is None or entry.status != "queued":
        # Already handled (or the row vanished) — nothing to do.
        return None

    entry.status = "processing"
    entry.application_started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        job_result = await db.execute(select(Job).where(Job.id == entry.job_id))
        job = job_result.scalar_one()
        user_result = await db.execute(select(User).where(User.id == entry.user_id))
        user = user_result.scalar_one()

        application = Application(
            user_id=entry.user_id,
            job_id=entry.job_id,
            status="ready_for_review",
            match_score=entry.match_score,
            discovered_at=entry.detected_at or entry.created_at,
        )
        application.events.append(
            ApplicationEvent(
                event_type="status_changed",
                message=(
                    f"Rapid Apply screened this job (match {entry.match_score}%, priority P{entry.priority}) "
                    "and queued it for automated application."
                ),
            )
        )
        db.add(application)
        await db.flush()

        await attempt_submission(db, application, job, user)

        entry.application_id = application.id
        entry.application_completed_at = datetime.now(timezone.utc)
        entry.status = "completed"
        logger.info(
            "rapid_apply_processed",
            entry_id=str(entry.id),
            application_id=str(application.id),
            final_status=application.status,
        )
    except Exception as exc:  # pragma: no cover - defensive; nothing in this path currently raises
        entry.status = "failed"
        entry.failure_reason = str(exc)
        logger.error("rapid_apply_processing_failed", entry_id=str(entry.id), error=str(exc))

    await db.commit()
    await db.refresh(entry)
    return entry


async def process_all_queued(db: AsyncSession, redis_client: Redis) -> list[RapidApplyQueueEntry]:
    processed: list[RapidApplyQueueEntry] = []
    for _ in range(MAX_PROCESS_PER_CYCLE):
        entry = await process_next(db, redis_client)
        if entry is None:
            break
        processed.append(entry)
    return processed


@dataclass
class LatencyStats:
    count: int = 0
    avg_detection_to_match_seconds: float | None = None
    avg_match_to_queue_seconds: float | None = None
    avg_application_seconds: float | None = None
    avg_total_seconds: float | None = None
    fastest_total_seconds: float | None = None


@dataclass
class RapidApplyStats:
    total_queued: int = 0
    queued: int = 0
    processing: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    queue_depth_by_priority: dict[int, int] = field(default_factory=dict)
    latency: LatencyStats = field(default_factory=LatencyStats)


def _seconds_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return (end - start).total_seconds()


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


async def get_stats(db: AsyncSession, user: User, redis_client: Redis) -> RapidApplyStats:
    result = await db.execute(select(RapidApplyQueueEntry).where(RapidApplyQueueEntry.user_id == user.id))
    entries = list(result.scalars().all())

    stats = RapidApplyStats(total_queued=len(entries))
    for entry in entries:
        if entry.status == "queued":
            stats.queued += 1
        elif entry.status == "processing":
            stats.processing += 1
        elif entry.status == "completed":
            stats.completed += 1
        elif entry.status == "skipped":
            stats.skipped += 1
        elif entry.status == "failed":
            stats.failed += 1

    queue = _queue_for(redis_client)
    stats.queue_depth_by_priority = await queue.queue_lengths()

    completed_entries = [e for e in entries if e.status == "completed"]
    detect_to_match = [
        s for e in completed_entries if (s := _seconds_between(e.detected_at, e.matched_at)) is not None
    ]
    match_to_queue = [
        s for e in completed_entries if (s := _seconds_between(e.matched_at, e.queued_at)) is not None
    ]
    application_secs = [
        s
        for e in completed_entries
        if (s := _seconds_between(e.application_started_at, e.application_completed_at)) is not None
    ]
    total_secs = [
        s
        for e in completed_entries
        if (s := _seconds_between(e.source_posted_at or e.first_seen_at, e.application_completed_at)) is not None
    ]

    stats.latency = LatencyStats(
        count=len(completed_entries),
        avg_detection_to_match_seconds=_avg(detect_to_match),
        avg_match_to_queue_seconds=_avg(match_to_queue),
        avg_application_seconds=_avg(application_secs),
        avg_total_seconds=_avg(total_secs),
        fastest_total_seconds=round(min(total_secs), 3) if total_secs else None,
    )
    return stats


async def run_cycle(db: AsyncSession, redis_client: Redis) -> CycleResult:
    """One full Rapid Apply cycle: detect+screen+queue, then drain the
    queue. This is what both the manual API endpoint and the Celery
    scheduled task call — one code path, one behavior."""
    detection = await detect_and_enqueue(db, redis_client)
    processed = await process_all_queued(db, redis_client)
    completed = sum(1 for e in processed if e.status == "completed")
    failed = sum(1 for e in processed if e.status == "failed")
    return CycleResult(detection=detection, processed=len(processed), completed=completed, failed=failed)
