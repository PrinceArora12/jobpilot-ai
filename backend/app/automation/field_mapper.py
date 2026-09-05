"""
Semantic field mapper — spec section 59. Deterministic first: every field
is matched against a fixed alias table by its HTML `name` attribute, never
guessed by an LLM (a form field is either recognized or it isn't — there's
no ambiguity worth spending an AI call on, and no risk of a hallucinated
mapping). A field that doesn't clear the confidence bar is never filled;
`run_application_automation` treats any *required* unmapped field as a
failsafe stop rather than submitting a guess (spec's "never fabricate"
rule applies just as much to form answers as to resume content).
"""
from dataclasses import dataclass

from app.models.job import Job
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User

CONFIDENT_MATCH = 1.0
FUZZY_MATCH = 0.6
CONFIDENCE_THRESHOLD = 0.6  # fuzzy matches are still trusted; anything below this is not

# Exact `name` attributes this build recognizes out of the box.
EXACT_ALIASES: dict[str, str] = {
    "full_name": "name",
    "name": "name",
    "applicant_name": "name",
    "email": "email",
    "email_address": "email",
    "phone": "phone",
    "phone_number": "phone",
    "mobile": "phone",
    "linkedin_url": "linkedin",
    "linkedin": "linkedin",
    "resume": "resume",
    "cv": "resume",
    "resume_file": "resume",
    "cover_letter": "cover_letter",
    "message": "cover_letter",
}

# Substrings checked when a field's exact name isn't in the alias table
# above (e.g. a provider names it "candidate_phone_number").
FUZZY_SUBSTRINGS: dict[str, str] = {
    "name": "name",
    "email": "email",
    "phone": "phone",
    "linkedin": "linkedin",
    "resume": "resume",
    "cv": "resume",
    "cover": "cover_letter",
}


@dataclass
class FormField:
    name: str
    field_type: str  # text | email | tel | file | textarea | ...
    required: bool


@dataclass
class MappedField:
    field: FormField
    canonical: str
    value: str
    confidence: float


@dataclass
class MappingResult:
    mapped: list[MappedField]
    unmapped_required: list[FormField]


def _classify(field_name: str) -> tuple[str | None, float]:
    key = field_name.strip().lower()
    if key in EXACT_ALIASES:
        return EXACT_ALIASES[key], CONFIDENT_MATCH
    for substring, canonical in FUZZY_SUBSTRINGS.items():
        if substring in key:
            return canonical, FUZZY_MATCH
    return None, 0.0


def _resolve_value(
    canonical: str,
    profile: Profile,
    user: User,
    resume: Resume | None,
    job: Job,
    matched_skills: list[str],
) -> str | None:
    if canonical == "name":
        full_name = " ".join(part for part in [profile.first_name, profile.last_name] if part).strip()
        return full_name or None
    if canonical == "email":
        return user.email
    if canonical == "phone":
        return profile.phone
    if canonical == "linkedin":
        return profile.linkedin_url
    if canonical == "resume":
        return resume.file_path if resume else None
    if canonical == "cover_letter":
        # Deterministic, entirely grounded in real data already on hand —
        # never an AI-generated claim. Phase 9 adds a smarter, still
        # grounded version; this is the honest placeholder until then.
        if matched_skills:
            skills_clause = f"my experience with {', '.join(matched_skills[:3])}"
        else:
            skills_clause = "my background"
        return f"I'm excited to apply for {job.title} at {job.company.name}, where {skills_clause} would let me contribute right away."
    return None


def map_fields(
    fields: list[FormField],
    profile: Profile,
    user: User,
    resume: Resume | None,
    job: Job,
    matched_skills: list[str],
) -> MappingResult:
    mapped: list[MappedField] = []
    unmapped_required: list[FormField] = []

    for field in fields:
        canonical, confidence = _classify(field.name)
        value = _resolve_value(canonical, profile, user, resume, job, matched_skills) if canonical else None

        if canonical is None or confidence < CONFIDENCE_THRESHOLD or not value:
            if field.required:
                unmapped_required.append(field)
            continue

        mapped.append(MappedField(field=field, canonical=canonical, value=value, confidence=confidence))

    return MappingResult(mapped=mapped, unmapped_required=unmapped_required)
