"""
Job normalization — spec section 12. Converts any adapter's raw,
provider-shaped dict into the one canonical schema every downstream stage
(dedup, matching, rapid apply) relies on.
"""
from datetime import datetime, timezone
from typing import Any


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        # Epoch millis (Lever) vs seconds — millis if it's a implausibly large "seconds" value.
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def normalize_job(raw: dict[str, Any], source: str) -> dict[str, Any]:
    """
    Returns the canonical job schema:
    external_id, title, company, location, remote, employment_type,
    experience_level, salary, description, requirements, skills, url,
    source, posted_at, deadline.
    """
    posted_at = _parse_datetime(raw.get("posted_at")) or datetime.now(timezone.utc)

    return {
        "external_id": str(raw.get("external_id") or raw.get("id") or raw["url"]),
        "title": (raw.get("title") or "").strip(),
        "company": (raw.get("company") or "Unknown Company").strip(),
        "location": raw.get("location"),
        "remote": bool(raw.get("remote", False)),
        "employment_type": raw.get("employment_type"),
        "experience_level": raw.get("experience_level"),
        "salary": raw.get("salary"),
        "description": raw.get("description") or "",
        "requirements": list(raw.get("requirements") or []),
        "skills": list(raw.get("skills") or []),
        "url": raw["url"],
        "source": source,
        "posted_at": posted_at,
        "deadline": _parse_datetime(raw.get("deadline")),
    }
