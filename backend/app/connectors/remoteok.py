"""
RemoteOK adapter — uses RemoteOK's free, public, unauthenticated JSON feed
(https://remoteok.com/api). No signup, no key. RemoteOK's own docs ask
clients to send a real User-Agent (a blank/default one gets blocked), so
this identifies the app rather than spoofing a browser.
"""
from typing import Any

import httpx

from app.connectors.base import JobSource

REMOTEOK_API_URL = "https://remoteok.com/api"


class RemoteOKAdapter(JobSource):
    source_name = "remoteok"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        headers = {"User-Agent": "JobPilotAI/1.0 (personal job aggregator; contact via app owner)"}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            response = await client.get(REMOTEOK_API_URL)
            response.raise_for_status()
            data = response.json()

        raw_jobs = []
        for item in data:
            # RemoteOK's first array element is a legal/notice object, not a job.
            if not isinstance(item, dict) or "id" not in item or "position" not in item:
                continue
            salary = None
            if item.get("salary_min") and item.get("salary_max"):
                salary = f"${item['salary_min']:,} - ${item['salary_max']:,}"
            raw_jobs.append(
                {
                    "external_id": str(item.get("id")),
                    "title": item.get("position"),
                    "company": item.get("company"),
                    "location": item.get("location") or "Remote",
                    "remote": True,
                    "salary": salary,
                    "description": item.get("description"),
                    "skills": item.get("tags") or [],
                    "url": item.get("url"),
                    "posted_at": item.get("date"),
                }
            )
        return raw_jobs
