from app.services.job_dedup import compute_content_hash
from app.services.job_normalizer import normalize_job


def test_normalize_fills_canonical_schema():
    raw = {
        "title": "  Software Engineer Intern ",
        "company": "Acme",
        "location": "Remote - India",
        "remote": True,
        "url": "https://acme.example/jobs/1",
        "skills": ["Python", "SQL"],
        "posted_at": "2026-09-04T13:15:00Z",
    }
    normalized = normalize_job(raw, source="mock")
    assert normalized["title"] == "Software Engineer Intern"
    assert normalized["source"] == "mock"
    assert normalized["skills"] == ["Python", "SQL"]
    assert normalized["posted_at"].year == 2026


def test_normalize_epoch_millis_datetime():
    raw = {"title": "X", "company": "Y", "url": "https://x/1", "posted_at": 1_757_000_000_000}
    normalized = normalize_job(raw, source="lever")
    assert normalized["posted_at"].year >= 2025


def test_content_hash_stable_for_same_job():
    job_a = normalize_job(
        {"title": "SWE Intern", "company": "Acme", "location": "Remote", "description": "Build things", "url": "u1"},
        source="mock",
    )
    job_b = normalize_job(
        {"title": " SWE Intern ", "company": "Acme", "location": "remote", "description": "Build things", "url": "u2"},
        source="greenhouse",
    )
    assert compute_content_hash(job_a) == compute_content_hash(job_b)


def test_content_hash_differs_for_different_jobs():
    job_a = normalize_job({"title": "SWE Intern", "company": "Acme", "url": "u1"}, source="mock")
    job_b = normalize_job({"title": "Data Analyst Intern", "company": "Acme", "url": "u2"}, source="mock")
    assert compute_content_hash(job_a) != compute_content_hash(job_b)
