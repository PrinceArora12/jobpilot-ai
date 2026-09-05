"""
Mock job source — spec section 56. Backed by the mock_job_postings table so
`POST /api/mock/jobs` (simulating a company publishing a job) can be drained
by this adapter exactly like a real poller would drain a real feed. Used
for local development and the Phase 7/8 end-to-end rapid-apply tests
without touching any real job portal.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import JobSource
from app.models.mock_job_posting import MockJobPosting


class MockJobSource(JobSource):
    source_name = "mock"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(MockJobPosting).where(MockJobPosting.consumed_at.is_(None)).order_by(MockJobPosting.created_at)
        )
        postings = list(result.scalars().all())

        jobs = []
        for posting in postings:
            raw = dict(posting.payload)
            raw["external_id"] = raw.get("external_id") or str(posting.id)
            raw["posted_at"] = raw.get("posted_at") or posting.source_posted_at.isoformat()
            jobs.append(raw)
            posting.consumed_at = datetime.now(timezone.utc)

        if postings:
            await self.db.commit()
        return jobs
