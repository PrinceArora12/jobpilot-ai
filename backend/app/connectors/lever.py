"""
Lever adapter — uses Lever's public Postings API
(https://api.lever.co/v0/postings/{company}), which Lever publishes
specifically for reading a company's live job postings. No login, no
scraping.
"""
from typing import Any

import httpx

from app.connectors.base import JobSource

LEVER_API_BASE = "https://api.lever.co/v0/postings"


class LeverAdapter(JobSource):
    source_name = "lever"

    def __init__(self, company_slug: str, timeout: float = 10.0):
        self.company_slug = company_slug
        self.timeout = timeout

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        url = f"{LEVER_API_BASE}/{self.company_slug}?mode=json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        raw_jobs = []
        for item in data:
            categories = item.get("categories", {})
            raw_jobs.append(
                {
                    "external_id": item.get("id"),
                    "title": item.get("text"),
                    "company": self.company_slug,
                    "location": categories.get("location"),
                    "remote": "remote" in (categories.get("location") or "").lower(),
                    "employment_type": categories.get("commitment"),
                    "description": item.get("descriptionPlain") or item.get("description"),
                    "url": item.get("hostedUrl"),
                    "posted_at": item.get("createdAt"),
                }
            )
        return raw_jobs
