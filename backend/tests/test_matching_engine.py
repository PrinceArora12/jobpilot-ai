from types import SimpleNamespace

import pytest

from app.agents.matching_engine import compute_match, explain_match
from app.ai.mock_provider import MockAIProvider
from app.services.eligibility import check_eligibility


def make_profile(**overrides):
    defaults = dict(
        skills=[],
        preferred_skills=[],
        education=[],
        experience_level=None,
        preferred_locations=[],
        preferred_roles=[],
        job_types=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_job(**overrides):
    defaults = dict(
        title="Software Engineer Intern",
        skills=["Python", "SQL"],
        experience_level="fresher",
        remote=True,
        location=None,
        employment_type="internship",
        company=SimpleNamespace(is_blocked=False, name="Acme"),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_full_skill_overlap_scores_100_on_skills():
    profile = make_profile(skills=[SimpleNamespace(name="Python"), SimpleNamespace(name="SQL")])
    job = make_job()
    result = compute_match(profile, job)
    assert result.skills_score == 100
    assert set(result.matched_skills) == {"Python", "SQL"}
    assert result.missing_skills == []


def test_partial_skill_overlap_reports_missing():
    profile = make_profile(skills=[SimpleNamespace(name="Python")])
    job = make_job(skills=["Python", "SQL", "Kafka"])
    result = compute_match(profile, job)
    assert result.skills_score == 33  # 1/3 rounded
    assert result.matched_skills == ["Python"]
    assert set(result.missing_skills) == {"SQL", "Kafka"}


def test_no_skills_required_scores_100():
    profile = make_profile()
    job = make_job(skills=[])
    result = compute_match(profile, job)
    assert result.skills_score == 100


def test_experience_level_mismatch_scores_low():
    profile = make_profile(experience_level="4+")
    job = make_job(experience_level="fresher")
    result = compute_match(profile, job)
    assert result.experience_score == 40


def test_fresher_and_entry_level_are_compatible():
    profile = make_profile(experience_level="entry_level")
    job = make_job(experience_level="fresher")
    result = compute_match(profile, job)
    assert result.experience_score == 90


def test_remote_job_scores_full_location():
    profile = make_profile(preferred_locations=["Bengaluru"])
    job = make_job(remote=True, location=None)
    result = compute_match(profile, job)
    assert result.location_score == 100


def test_onsite_job_outside_preferred_locations_scores_low():
    profile = make_profile(preferred_locations=["Bengaluru"])
    job = make_job(remote=False, location="New York")
    result = compute_match(profile, job)
    assert result.location_score == 30


def test_overall_score_is_weighted_average():
    profile = make_profile(skills=[SimpleNamespace(name="Python"), SimpleNamespace(name="SQL")])
    job = make_job()
    result = compute_match(profile, job)
    # skills=100*.35 + education(no edu)=40*.15 + experience(unknown pref)=70*.20
    # + location(remote)=100*.15 + role(no pref)=70*.15
    expected = round(100 * 0.35 + 40 * 0.15 + 70 * 0.20 + 100 * 0.15 + 70 * 0.15)
    assert result.overall_score == expected


def test_eligibility_blocks_wrong_job_type():
    profile = make_profile(job_types=["full_time"])
    job = make_job(employment_type="internship")
    result = check_eligibility(profile, job)
    assert result.passed is False
    assert "internship" in result.reasons[0]


def test_eligibility_blocks_blocked_company():
    profile = make_profile()
    job = make_job(company=SimpleNamespace(is_blocked=True, name="BadCo"))
    result = check_eligibility(profile, job)
    assert result.passed is False
    assert "BadCo" in result.reasons[0]


def test_eligibility_passes_with_no_preferences_set():
    profile = make_profile()
    job = make_job()
    result = check_eligibility(profile, job)
    assert result.passed is True
    assert result.reasons == []


@pytest.mark.asyncio
async def test_explanation_never_claims_unmatched_skill():
    profile = make_profile(skills=[SimpleNamespace(name="Python")])
    job = make_job(skills=["Python", "Kubernetes"])
    breakdown = compute_match(profile, job)
    explanation = await explain_match(breakdown, job, MockAIProvider())
    assert "Python" in explanation
    assert "Missing" in explanation and "Kubernetes" in explanation
