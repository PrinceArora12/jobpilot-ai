"""
JobSource adapter interface — spec section 11.

Every adapter returns *raw* provider-shaped dicts; normalization into the
canonical schema (spec section 12) happens once, centrally, in
app/services/job_normalizer.py — adapters never normalize themselves. This
keeps adding a new source a matter of writing fetch_jobs() only.
"""
from abc import ABC, abstractmethod
from typing import Any


class JobSource(ABC):
    """Base interface every job source adapter implements."""

    #: short machine-readable name stored on Job.source
    source_name: str = "unknown"

    @abstractmethod
    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """Return a list of raw, provider-shaped job postings."""
        raise NotImplementedError
