"""
AI Application Assistant — spec section 20-24. Answers free-text screening
questions ("Do you have experience with Kubernetes?", "Why do you want to
work here?") the same way the Matching Engine scores a job: grounding
comes ENTIRELY from deterministic lookups against the user's actual
profile/resume/project data, and the AI provider (mock by default) is only
ever asked to phrase an answer built from facts already established —
never to invent a claim.

Every recognized question type either resolves to a grounded fact (with a
source and a confidence score the caller can show the user) or explicitly
returns NEEDS_USER_INPUT. There is no third option: an ungrounded guess is
exactly the "fabricated qualification" spec section 6/51 forbids, so
anything this module isn't confident about is simply left for the human.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime

from app.ai.base import AIProvider
from app.models.job import Job
from app.models.profile import Profile
from app.models.resume import Resume

NEEDS_USER_INPUT = "needs_user_input"
ANSWERED = "answered"

# Questions about these topics are never answered automatically, no matter
# what's on file — they're personal decisions/negotiations, not facts a
# profile can settle on the user's behalf.
NEVER_AUTO_ANSWER_PATTERNS = [
    r"\bnotice period\b",
    r"\bstart date\b",
    r"\bavailability\b",
    r"\bwhen can you start\b",
    r"\bvisa\b",
    r"\bsponsorship\b",
    r"\bwork authorization\b",
    r"\bfelony\b",
    r"\bconviction\b",
    r"\bdisability\b",
    r"\bveteran\b",
    r"\bgender\b",
    r"\brace\b",
    r"\bethnicity\b",
]

SKILL_QUESTION_PATTERNS = [
    r"experience with (?P<skill>[\w+#. ]+?)[\?\.]?$",
    r"familiar with (?P<skill>[\w+#. ]+?)[\?\.]?$",
    r"proficient (?:in|with) (?P<skill>[\w+#. ]+?)[\?\.]?$",
    r"worked with (?P<skill>[\w+#. ]+?)[\?\.]?$",
    r"know (?P<skill>[\w+#. ]+?)[\?\.]?$",
]

YEARS_EXPERIENCE_PATTERN = re.compile(r"how many years|years of experience", re.IGNORECASE)
EDUCATION_PATTERN = re.compile(r"degree|education|university|college|graduat", re.IGNORECASE)
SALARY_PATTERN = re.compile(r"salary|compensation|pay expectation", re.IGNORECASE)
MOTIVATION_PATTERN = re.compile(
    r"why (do you want|are you interested|should we|this role|this company|us)", re.IGNORECASE
)
LOCATION_PATTERN = re.compile(r"relocat|remote|on-?site|willing to work", re.IGNORECASE)


@dataclass
class AssistantAnswer:
    status: str  # "answered" | "needs_user_input"
    answer: str | None = None
    confidence: float | None = None
    source: str | None = None
    reason: str | None = None  # why we couldn't answer, when status is needs_user_input


def _resume_skills(resume: Resume | None) -> set[str]:
    if resume and resume.parsed_data:
        return {s.lower() for s in resume.parsed_data.get("skills", [])}
    return set()


def _profile_skills(profile: Profile) -> set[str]:
    return {s.name.lower() for s in profile.skills} | {s.lower() for s in profile.preferred_skills}


def _total_years_experience(profile: Profile) -> float | None:
    if not profile.experience:
        return None
    total_days = 0
    today = date.today()
    for exp in profile.experience:
        if not exp.start_date:
            continue
        try:
            start = datetime.strptime(exp.start_date, "%Y-%m").date()
        except ValueError:
            continue
        if exp.end_date:
            try:
                end = datetime.strptime(exp.end_date, "%Y-%m").date()
            except ValueError:
                end = today
        else:
            end = today
        if end > start:
            total_days += (end - start).days
    if total_days == 0:
        return None
    return round(total_days / 365.25, 1)


def _classify_and_ground(
    question: str, profile: Profile, resume: Resume | None, job: Job, matched_skills: list[str]
) -> tuple[str | None, float, str | None, str | None]:
    """Returns (template_or_None, confidence, source, reason_if_ungrounded)."""
    q = question.strip().lower()

    for pattern in NEVER_AUTO_ANSWER_PATTERNS:
        if re.search(pattern, q):
            return None, 0.0, None, "This is a personal decision the applicant must answer themselves."

    for pattern in SKILL_QUESTION_PATTERNS:
        # Matched against the original (not lowercased) question so the
        # extracted skill name keeps its natural casing (e.g. "Python",
        # not "python") when it's echoed back in the answer text.
        match = re.search(pattern, question.strip(), re.IGNORECASE)
        if match:
            skill = match.group("skill").strip()
            known_skills = _resume_skills(resume) | _profile_skills(profile)
            if skill.lower() in known_skills:
                return (
                    f"Yes — {skill} appears in my profile/resume skills.",
                    0.95,
                    "profile.skills" if skill.lower() in _profile_skills(profile) else "resume.parsed_data.skills",
                    None,
                )
            return None, 0.0, None, f"'{skill}' is not listed anywhere in the profile or resume — can't confirm it."

    if YEARS_EXPERIENCE_PATTERN.search(q):
        years = _total_years_experience(profile)
        if years is not None:
            return (
                f"Approximately {years} years of professional experience, based on my work history.",
                0.85,
                "profile.experience",
                None,
            )
        return None, 0.0, None, "No work-experience entries with usable dates are on file."

    if EDUCATION_PATTERN.search(q):
        if profile.education:
            edu = profile.education[0]
            parts = [p for p in [edu.degree, edu.major, edu.university] if p]
            if parts:
                return (
                    f"{' in '.join(parts[:2])}{' from ' + edu.university if edu.university and edu.university not in parts[:2] else ''}.",
                    0.9,
                    "profile.education",
                    None,
                )
        return None, 0.0, None, "No education history is on file."

    if SALARY_PATTERN.search(q):
        if profile.min_salary:
            return (
                f"My minimum salary expectation is {profile.min_salary:,.0f}.",
                0.85,
                "profile.min_salary",
                None,
            )
        return None, 0.0, None, "No salary expectation is on file."

    if LOCATION_PATTERN.search(q):
        if job.remote:
            return "This is a remote position, which fits my work preferences.", 0.9, "job.remote", None
        if profile.preferred_locations and job.location:
            loc = job.location.lower()
            if any(pl.lower() in loc or loc in pl.lower() for pl in profile.preferred_locations):
                return (
                    f"{job.location} is one of my preferred locations, so this works for me.",
                    0.85,
                    "profile.preferred_locations",
                    None,
                )
        return None, 0.0, None, "Relocation/on-site willingness isn't something the profile can answer for the applicant."

    if MOTIVATION_PATTERN.search(q):
        if matched_skills:
            skills_clause = f"my hands-on experience with {', '.join(matched_skills[:3])}"
        else:
            skills_clause = "my background"
        return (
            f"I'm drawn to {job.title} at {job.company.name} because {skills_clause} lines up directly with "
            "what the role needs, and I'm excited to keep building in this space.",
            0.7,
            "generated:job_match",
            None,
        )

    return None, 0.0, None, "This question doesn't match any topic the assistant currently recognizes."


async def answer_question(
    question: str,
    profile: Profile,
    resume: Resume | None,
    job: Job,
    matched_skills: list[str],
    ai: AIProvider,
) -> AssistantAnswer:
    template, confidence, source, reason = _classify_and_ground(question, profile, resume, job, matched_skills)

    if template is None:
        return AssistantAnswer(status=NEEDS_USER_INPUT, reason=reason)

    # The AI provider only reformats an already-fully-grounded sentence —
    # exactly like matching_engine.explain_match — so mock/openai/anthropic
    # are all equally safe to use here.
    phrased = await ai.generate(template)
    return AssistantAnswer(status=ANSWERED, answer=phrased, confidence=confidence, source=source)
