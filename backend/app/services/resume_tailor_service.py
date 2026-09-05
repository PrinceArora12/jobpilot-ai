"""
Resume tailoring — spec section 24. Deliberately limited to reordering the
skills the resume already lists so the ones a specific job cares about
appear first, plus surfacing which listed skills matched. It NEVER adds a
skill that wasn't already on the resume and NEVER removes one — that would
mean fabricating or hiding a qualification, which spec section 6/51
forbids outright. `apply_tailoring` enforces this as a hard invariant
(same multiset of skills in and out), not just a convention, and nothing
is written back to the resume until the caller (a human, via the
"preview then apply" API split) explicitly approves the proposed order.
"""
from dataclasses import dataclass

from app.models.job import Job
from app.models.resume import Resume


@dataclass
class TailorPreview:
    original_order: list[str]
    suggested_order: list[str]
    matched_keywords: list[str]
    changed: bool


def preview_tailoring(resume: Resume, job: Job) -> TailorPreview:
    original: list[str] = list((resume.parsed_data or {}).get("skills", []))
    job_skills_lower = {s.lower() for s in job.skills}

    matched = [s for s in original if s.lower() in job_skills_lower]
    unmatched = [s for s in original if s.lower() not in job_skills_lower]
    suggested = matched + unmatched  # matched skills first, everything else keeps its relative order

    return TailorPreview(
        original_order=original,
        suggested_order=suggested,
        matched_keywords=matched,
        changed=suggested != original,
    )


class TailoringValidationError(ValueError):
    pass


def apply_tailoring(resume: Resume, approved_order: list[str]) -> Resume:
    original: list[str] = list((resume.parsed_data or {}).get("skills", []))

    if sorted(s.lower() for s in approved_order) != sorted(s.lower() for s in original):
        raise TailoringValidationError(
            "Approved skill order must contain exactly the same skills as the resume already lists — "
            "tailoring only reorders, it never adds or removes a qualification."
        )

    parsed_data = dict(resume.parsed_data or {})
    parsed_data["skills"] = approved_order
    resume.parsed_data = parsed_data
    return resume
