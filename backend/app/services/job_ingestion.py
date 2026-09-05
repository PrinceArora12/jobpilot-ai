"""
Job ingestion pipeline: normalize -> deduplicate -> upsert Company -> store
Job. This is the single choke point every source (mock, Greenhouse, Lever,
future adapters) and every caller (manual sync endpoint in Phase 4, the
Rapid Apply watcher in Phase 7) funnels through, so dedup and normalization
rules only exist once.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.job import Company, Job
from app.services.job_dedup import compute_content_hash
from app.services.job_normalizer import normalize_job

logger = get_logger(__name__)


async def _get_or_create_company(db: AsyncSession, name: str) -> Company:
    result = await db.execute(select(Company).where(Company.name == name))
    company = result.scalar_one_or_none()
    if company is None:
        company = Company(name=name)
        db.add(company)
        await db.flush()
    return company


async def find_duplicate(db: AsyncSession, normalized: dict[str, Any], content_hash: str) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.source == normalized["source"], Job.external_id == normalized["external_id"])
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    result = await db.execute(select(Job).where(Job.url == normalized["url"]))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    result = await db.execute(select(Job).where(Job.content_hash == content_hash))
    return result.scalar_one_or_none()


async def ingest_job(db: AsyncSession, raw: dict[str, Any], source: str) -> tuple[Job, bool]:
    """Returns (job, was_newly_created). Never creates a duplicate row."""
    normalized = normalize_job(raw, source)
    content_hash = compute_content_hash(normalized)

    duplicate = await find_duplicate(db, normalized, content_hash)
    if duplicate is not None:
        logger.info("job_deduplicated", external_id=normalized["external_id"], source=source)
        return duplicate, False

    company = await _get_or_create_company(db, normalized["company"])

    job = Job(
        external_id=normalized["external_id"],
        source=normalized["source"],
        title=normalized["title"],
        company_id=company.id,
        location=normalized["location"],
        remote=normalized["remote"],
        employment_type=normalized["employment_type"],
        experience_level=normalized["experience_level"],
        salary=normalized["salary"],
        description=normalized["description"],
        requirements=normalized["requirements"],
        skills=normalized["skills"],
        url=normalized["url"],
        content_hash=content_hash,
        posted_at=normalized["posted_at"],
        deadline=normalized["deadline"],
        first_seen_at=datetime.now(timezone.utc),
        # Phase 8: only meaningful for mock jobs; any other source simply
        # keeps the "standard" default since it has no automatable form.
        automation_variant=raw.get("form_variant") or "standard",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info("job_detected", job_id=str(job.id), source=source, title=job.title)
    return job, True
