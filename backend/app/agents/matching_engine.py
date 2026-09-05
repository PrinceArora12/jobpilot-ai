"""
Matching Engine — spec section 17. One of the specialized agents from
section 43 (kept separate from Resume Analyzer / Job Analyzer / etc. rather
than one giant agent). The score itself is entirely deterministic math —
skill overlap, education presence, experience-level distance, location
fit, role keyword overlap — because none of that requires semantic
reasoning. The only place an AI provider is invoked is the human-readable
explanation, and even that is built from the already-computed numbers so
it can never claim a skill match that didn't happen.
"""
from dataclasses import dataclass

from app.ai.base import AIProvider
from app.models.job import Job
from app.models.profile import Profile

# Weights sum to 100 — spec section 17's breakdown.
WEIGHTS = {
    "skills": 0.35,
    "education": 0.15,
    "experience": 0.20,
    "location": 0.15,
    "role": 0.15,
}

EXPERIENCE_COMPATIBLE = {"fresher", "entry_level"}


@dataclass
class MatchBreakdown:
    overall_score: int
    skills_score: int
    education_score: int
    experience_score: int
    location_score: int
    role_score: int
    matched_skills: list[str]
    missing_skills: list[str]


def _collect_profile_skills(profile: Profile, resume_skills: list[str] | None = None) -> set[str]:
    skills = {s.name.lower() for s in profile.skills}
    skills |= {s.lower() for s in profile.preferred_skills}
    if resume_skills:
        skills |= {s.lower() for s in resume_skills}
    return skills


def _skills_score(profile_skills: set[str], job_skills: list[str]) -> tuple[int, list[str], list[str]]:
    if not job_skills:
        return 100, [], []
    job_skills_lower = {s.lower(): s for s in job_skills}
    matched = [original for lower, original in job_skills_lower.items() if lower in profile_skills]
    missing = [original for lower, original in job_skills_lower.items() if lower not in profile_skills]
    score = round(100 * len(matched) / len(job_skills))
    return score, matched, missing


def _education_score(profile: Profile) -> int:
    return 100 if profile.education else 40


def _experience_score(profile: Profile, job: Job) -> int:
    if not job.experience_level or not profile.experience_level:
        return 70  # unknown requirement — neutral, not a penalty
    if job.experience_level == profile.experience_level:
        return 100
    if {job.experience_level, profile.experience_level} <= EXPERIENCE_COMPATIBLE:
        return 90
    return 40


def _location_score(profile: Profile, job: Job) -> int:
    if job.remote:
        return 100
    if not profile.preferred_locations:
        return 70
    location = (job.location or "").lower()
    if any(loc.lower() in location or location in loc.lower() for loc in profile.preferred_locations):
        return 100
    return 30


def _role_score(profile: Profile, job: Job) -> int:
    if not profile.preferred_roles:
        return 70
    title = job.title.lower()
    if any(role.lower() in title or title in role.lower() for role in profile.preferred_roles):
        return 100
    # partial credit for shared words (e.g. "Software Engineer" vs "Software Engineer Intern")
    title_words = set(title.split())
    for role in profile.preferred_roles:
        if title_words & set(role.lower().split()):
            return 60
    return 20


def compute_match(profile: Profile, job: Job, resume_skills: list[str] | None = None) -> MatchBreakdown:
    profile_skills = _collect_profile_skills(profile, resume_skills)
    skills_score, matched, missing = _skills_score(profile_skills, job.skills)
    education_score = _education_score(profile)
    experience_score = _experience_score(profile, job)
    location_score = _location_score(profile, job)
    role_score = _role_score(profile, job)

    overall = round(
        skills_score * WEIGHTS["skills"]
        + education_score * WEIGHTS["education"]
        + experience_score * WEIGHTS["experience"]
        + location_score * WEIGHTS["location"]
        + role_score * WEIGHTS["role"]
    )

    return MatchBreakdown(
        overall_score=overall,
        skills_score=skills_score,
        education_score=education_score,
        experience_score=experience_score,
        location_score=location_score,
        role_score=role_score,
        matched_skills=matched,
        missing_skills=missing,
    )


async def explain_match(breakdown: MatchBreakdown, job: Job, ai: AIProvider) -> str:
    """Builds the explanation from already-computed numbers only — the AI
    provider (mock by default) formats it, it never invents new claims."""
    if breakdown.matched_skills:
        skills_clause = f"the role's need for {', '.join(breakdown.matched_skills)}, which your profile has"
    else:
        skills_clause = "the role, though no listed skills currently overlap with your profile"

    template = (
        f"{breakdown.overall_score}% match for {job.title}. Strongest fit: {skills_clause}."
    )
    if breakdown.missing_skills:
        template += f" Missing from your profile: {', '.join(breakdown.missing_skills)}."

    return await ai.generate(template)
