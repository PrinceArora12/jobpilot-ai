"""
Fast Eligibility Engine — spec section 16. Pure deterministic checks, no AI
call, so it can run before the (comparatively expensive) match scoring
step and reject obvious non-matches in well under a millisecond.
"""
from dataclasses import dataclass, field

from app.models.job import Job
from app.models.profile import Profile


@dataclass
class EligibilityResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def check_eligibility(profile: Profile, job: Job) -> EligibilityResult:
    reasons: list[str] = []

    if profile.job_types and job.employment_type and job.employment_type not in profile.job_types:
        reasons.append(f"Job type '{job.employment_type}' not in preferred types {profile.job_types}")

    if profile.preferred_locations and not job.remote:
        location = (job.location or "").lower()
        if not any(loc.lower() in location or location in loc.lower() for loc in profile.preferred_locations):
            reasons.append(f"Location '{job.location}' not in preferred locations")

    if profile.experience_level and job.experience_level and job.experience_level != profile.experience_level:
        # Fresher/entry-level are treated as compatible with each other.
        compatible = {"fresher", "entry_level"}
        if not ({profile.experience_level, job.experience_level} <= compatible):
            reasons.append(
                f"Experience level '{job.experience_level}' does not match profile '{profile.experience_level}'"
            )

    if job.company.is_blocked:
        reasons.append(f"Company '{job.company.name}' is blocked")

    return EligibilityResult(passed=len(reasons) == 0, reasons=reasons)
