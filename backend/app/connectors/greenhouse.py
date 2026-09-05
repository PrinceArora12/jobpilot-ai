"""
Greenhouse Job Board adapter — uses Greenhouse's public, unauthenticated
Job Board API (https://boards-api.greenhouse.io), which is explicitly
provided by Greenhouse for embedding/reading a company's open roles. No
login, no scraping, no rate-limit evasion.
"""
from typing import Any

import httpx

from app.connectors.base import JobSource

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseAdapter(JobSource):
    source_name = "greenhouse"

    def __init__(self, board_token: str, timeout: float = 10.0):
        self.board_token = board_token
        self.timeout = timeout

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        url = f"{GREENHOUSE_API_BASE}/{self.board_token}/jobs?content=true"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        raw_jobs = []
        for item in data.get("jobs", []):
            raw_jobs.append(
                {
                    "external_id": str(item.get("id")),
                    "title": item.get("title"),
                    "company": self.board_token,
                    "location": (item.get("location") or {}).get("name"),
                    "remote": "remote" in ((item.get("location") or {}).get("name") or "").lower(),
                    "description": item.get("content"),
                    "url": item.get("absolute_url"),
                    "posted_at": item.get("updated_at"),
                }
            )
        return raw_jobs
