"""
Arbeitnow adapter — uses Arbeitnow's free, public, unauthenticated Job Board
API (https://www.arbeitnow.com/api/job-board-api). No signup, no key. Mixed
remote/on-site listings, weighted toward Europe but not exclusively.
"""
from typing import Any

import httpx

from app.connectors.base import JobSource

ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowAdapter(JobSource):
    source_name = "arbeitnow"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(ARBEITNOW_API_URL)
            response.raise_for_status()
            data = response.json()

        raw_jobs = []
        for item in data.get("data", []):
            raw_jobs.append(
                {
                    "external_id": item.get("slug"),
                    "title": item.get("title"),
                    "company": item.get("company_name"),
                    "location": item.get("location"),
                    "remote": bool(item.get("remote", False)),
                    "employment_type": ",".join(item.get("job_types") or []) or None,
                    "description": item.get("description"),
                    "skills": item.get("tags") or [],
                    "url": item.get("url"),
                    "posted_at": item.get("created_at"),
                }
            )
        return raw_jobs
