"""
Unit tests for the AI Application Assistant's grounding logic (Phase 9).
Uses the mock AI provider (the project default) so these stay fast and
network-free — the assertions care about *what fact* was surfaced and
*whether it was grounded at all*, not about generated prose.
"""
from app.agents.application_assistant import ANSWERED, NEEDS_USER_INPUT, answer_question
from app.ai.mock_provider import MockAIProvider
from app.models.job import Company, Job
from app.models.profile import Education, Experience, Profile, Skill
from app.models.resume import Resume

AI = MockAIProvider()


def make_job(**overrides):
    company = Company(name=overrides.pop("company_name", "Acme Corp"))
    defaults = dict(
        external_id="ext-1",
        source="mock",
        title="Backend Engineer",
        location="Remote",
        remote=True,
        url="https://mock.jobpilot.ai/jobs/ext-1",
        content_hash="x" * 64,
        skills=["Python"],
    )
    defaults.update(overrides)
    job = Job(**defaults)
    job.company = company
    return job


def make_profile(**overrides):
    profile = Profile(user_id=overrides.pop("user_id", None))
    profile.skills = overrides.pop("skills", [])
    profile.preferred_skills = overrides.pop("preferred_skills", [])
    profile.preferred_locations = overrides.pop("preferred_locations", [])
    profile.education = overrides.pop("education", [])
    profile.experience = overrides.pop("experience", [])
    for key, value in overrides.items():
        setattr(profile, key, value)
    return profile


async def test_known_skill_question_is_answered_with_source():
    profile = make_profile(skills=[Skill(name="Python", category="technical")])
    job = make_job()
    result = await answer_question(
        "Do you have experience with Python?", profile, None, job, ["Python"], AI
    )
    assert result.status == ANSWERED
    assert result.source == "profile.skills"
    assert result.confidence is not None and result.confidence > 0.8
    assert "Python" in result.answer


async def test_unlisted_skill_question_needs_user_input_not_a_confident_no():
    profile = make_profile(skills=[Skill(name="Python", category="technical")])
    job = make_job()
    result = await answer_question(
        "Are you familiar with Kubernetes?", profile, None, job, [], AI
    )
    assert result.status == NEEDS_USER_INPUT
    assert result.answer is None
    assert "kubernetes" in result.reason.lower() or "Kubernetes" in result.reason


async def test_resume_skill_also_counts_as_grounding():
    profile = make_profile()
    resume = Resume(
        user_id=None,
        label="R",
        original_filename="r.pdf",
        file_path="/tmp/r.pdf",
        file_type="pdf",
        parsed_data={"skills": ["Rust"]},
    )
    job = make_job()
    result = await answer_question("Experience with Rust?", profile, resume, job, [], AI)
    assert result.status == ANSWERED
    assert result.source == "resume.parsed_data.skills"


async def test_years_of_experience_computed_from_dated_history():
    profile = make_profile(
        experience=[
            Experience(company="A", position="Dev", start_date="2020-01", end_date="2022-01"),
        ]
    )
    job = make_job()
    result = await answer_question("How many years of experience do you have?", profile, None, job, [], AI)
    assert result.status == ANSWERED
    assert "2.0" in result.answer
    assert result.source == "profile.experience"


async def test_no_experience_history_needs_user_input():
    profile = make_profile()
    job = make_job()
    result = await answer_question("Years of experience?", profile, None, job, [], AI)
    assert result.status == NEEDS_USER_INPUT


async def test_education_question_grounded_when_present():
    profile = make_profile(
        education=[Education(degree="B.S.", major="Computer Science", university="MIT", graduation_year=2020)]
    )
    job = make_job()
    result = await answer_question("What's your degree?", profile, None, job, [], AI)
    assert result.status == ANSWERED
    assert result.source == "profile.education"
    assert "Computer Science" in result.answer


async def test_salary_expectation_never_answered_without_stated_preference():
    profile = make_profile(min_salary=None)
    job = make_job()
    result = await answer_question("What's your salary expectation?", profile, None, job, [], AI)
    assert result.status == NEEDS_USER_INPUT


async def test_salary_expectation_grounded_when_stated_in_profile():
    profile = make_profile(min_salary=95000)
    job = make_job()
    result = await answer_question("What is your desired compensation?", profile, None, job, [], AI)
    assert result.status == ANSWERED
    assert result.source == "profile.min_salary"


async def test_sensitive_topics_are_never_auto_answered_regardless_of_data():
    profile = make_profile(min_salary=95000)
    job = make_job()
    for question in [
        "What is your notice period?",
        "Do you require visa sponsorship?",
        "When can you start?",
    ]:
        result = await answer_question(question, profile, None, job, [], AI)
        assert result.status == NEEDS_USER_INPUT, question


async def test_motivation_question_uses_matched_skills_and_job_data_only():
    profile = make_profile()
    job = make_job(title="Platform Engineer", company_name="Rocket Inc")
    result = await answer_question(
        "Why do you want to work at this company?", profile, None, job, ["Python", "AWS"], AI
    )
    assert result.status == ANSWERED
    assert "Rocket Inc" in result.answer
    assert "Platform Engineer" in result.answer
    assert result.confidence == 0.7


async def test_unrecognized_question_needs_user_input():
    profile = make_profile()
    job = make_job()
    result = await answer_question("Describe a time you disagreed with a coworker.", profile, None, job, [], AI)
    assert result.status == NEEDS_USER_INPUT
