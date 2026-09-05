"""
Remotive adapter — uses Remotive's free, public, unauthenticated Remote Jobs
API (https://remotive.com/api/remote-jobs). No signup, no key. Listings are
remote-only, sourced from Remotive's own job board.
"""
from typing import Any

import httpx

from app.connectors.base import JobSource

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveAdapter(JobSource):
    source_name = "remotive"

    def __init__(self, category: str | None = None, timeout: float = 10.0):
        self.category = category
        self.timeout = timeout

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        params = {"category": self.category} if self.category else {}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(REMOTIVE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        raw_jobs = []
        for item in data.get("jobs", []):
            raw_jobs.append(
                {
                    "external_id": str(item.get("id")),
                    "title": item.get("title"),
                    "company": item.get("company_name"),
                    "location": item.get("candidate_required_location"),
                    "remote": True,
                    "employment_type": item.get("job_type"),
                    "salary": item.get("salary") or None,
                    "description": item.get("description"),
                    "skills": item.get("tags") or [],
                    "url": item.get("url"),
                    "posted_at": item.get("publication_date"),
                }
            )
        return raw_jobs
