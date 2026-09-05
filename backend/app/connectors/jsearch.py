"""
JSearch adapter (via RapidAPI) — the compliant path to LinkedIn/Indeed/
Naukri/Glassdoor-style postings. JobPilot AI never scrapes those sites
directly: all of them explicitly prohibit automated scraping in their
Terms of Service, actively block/ban scrapers, and gate real job data
behind paid partner APIs individual developers can't get approved for.
JSearch is a third-party aggregator that indexes Google for Jobs (which
itself aggregates LinkedIn, Indeed, Naukri, Glassdoor, ZipRecruiter, and
company career pages) and republishes it through one legitimate,
ToS-compliant API with a free tier.

Sign up (free) at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch to
get an API key. Inactive unless JSEARCH_API_KEY is configured.
"""
from typing import Any

import httpx

from app.connectors.base import JobSource

JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"


class JSearchAdapter(JobSource):
    source_name = "jsearch"

    def __init__(self, query: str, api_key: str, timeout: float = 15.0):
        self.query = query
        self.api_key = api_key
        self.timeout = timeout

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        params = {"query": self.query, "page": "1", "num_pages": "1"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(JSEARCH_API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        raw_jobs = []
        for item in data.get("data", []):
            location_bits = [item.get("job_city"), item.get("job_country")]
            raw_jobs.append(
                {
                    "external_id": item.get("job_id"),
                    "title": item.get("job_title"),
                    "company": item.get("employer_name"),
                    "location": ", ".join(b for b in location_bits if b) or None,
                    "remote": bool(item.get("job_is_remote", False)),
                    "employment_type": item.get("job_employment_type"),
                    "description": item.get("job_description"),
                    "skills": item.get("job_required_skills") or [],
                    "url": item.get("job_apply_link"),
                    "posted_at": item.get("job_posted_at_datetime_utc"),
                }
            )
        return raw_jobs
