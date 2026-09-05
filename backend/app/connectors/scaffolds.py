"""
Adapter scaffolds — spec section 11 lists CompanyCareerAdapter, WorkdayAdapter,
and PublicFeedAdapter/APIAdapter alongside Greenhouse/Lever. Those two are
implemented for real (public, unauthenticated APIs). These three are left as
scaffolds rather than faked, because each one only becomes real automation
once it targets one specific, permitted source:

- CompanyCareerAdapter: scraping/parsing an arbitrary company careers page is
  only compliant when that specific site's terms allow automated access —
  there's no generic implementation that's safe for every company.
- WorkdayAdapter: Workday tenants each expose their own CXS JSON endpoint
  (no universal public API); wiring one requires picking a specific tenant.
- PublicFeedAdapter / APIAdapter: intentionally generic — implement per
  feed/API once a specific, permitted RSS feed or JSON API is chosen.

Per spec section 76 rule 9 ("do not create fake/mock production
functionality unless clearly labeled"), these raise NotImplementedError
instead of returning fabricated data.
"""
from typing import Any

from app.connectors.base import JobSource


class CompanyCareerAdapter(JobSource):
    source_name = "company_career_page"

    def __init__(self, company_name: str, careers_url: str):
        self.company_name = company_name
        self.careers_url = careers_url

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        raise NotImplementedError(
            f"No permitted, site-specific parser configured for {self.careers_url}. "
            "Implement one only after confirming that site's terms allow automated access."
        )


class WorkdayAdapter(JobSource):
    source_name = "workday"

    def __init__(self, tenant: str, site: str):
        self.tenant = tenant
        self.site = site

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        raise NotImplementedError(
            f"Workday tenant '{self.tenant}/{self.site}' is not configured. "
            "Each Workday tenant needs its own CXS endpoint wired up explicitly."
        )


class PublicFeedAdapter(JobSource):
    source_name = "public_feed"

    def __init__(self, feed_url: str):
        self.feed_url = feed_url

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        raise NotImplementedError(f"RSS/public feed at {self.feed_url} is not configured yet.")


class APIAdapter(JobSource):
    source_name = "api"

    def __init__(self, api_url: str):
        self.api_url = api_url

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        raise NotImplementedError(f"Generic API source {self.api_url} is not configured yet.")
