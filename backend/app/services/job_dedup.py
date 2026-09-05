"""
Job deduplication — spec section 15.

Two jobs are the same opportunity if they share (source, external_id), or
the same canonical URL, or — as a last resort, for sources that reuse URLs
or omit stable IDs — the same content hash (company + title + location +
a description prefix, normalized). Hashing catches near-duplicates from
different feeds without needing embeddings for an MVP.
"""
import hashlib
import re
from typing import Any


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def compute_content_hash(normalized_job: dict[str, Any]) -> str:
    parts = [
        _normalize_text(normalized_job.get("company", "")),
        _normalize_text(normalized_job.get("title", "")),
        _normalize_text(normalized_job.get("location") or ""),
        _normalize_text((normalized_job.get("description") or "")[:500]),
    ]
    digest_input = "|".join(parts).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()
