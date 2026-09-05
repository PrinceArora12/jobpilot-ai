"""Unit tests for the deterministic resume parser (no I/O)."""
from app.services.resume_parser import parse_resume

SAMPLE_TEXT = """Ankita Makkar
ankita@example.com
+91 98765 43210
linkedin.com/in/ankita-makkar
github.com/ankitamakkar

EDUCATION
B.Tech Computer Science, IIT Guwahati, 2027

EXPERIENCE
Software Engineer, Walmart Global Tech, 2018-Present

SKILLS
Python, Java, Kafka, Kubernetes, PostgreSQL, AWS

PROJECTS
Trip Planner - FastAPI + Next.js AI trip planning app

CERTIFICATIONS
AWS Certified Developer - Amazon - 2023
"""


def test_parses_contact_info():
    result = parse_resume(SAMPLE_TEXT)
    assert result["name"] == "Ankita Makkar"
    assert result["email"] == "ankita@example.com"
    assert "98765" in result["phone"]
    assert "linkedin.com/in/ankita-makkar" in result["links"]["linkedin"]
    assert "github.com/ankitamakkar" in result["links"]["github"]


def test_parses_skills_deterministically():
    result = parse_resume(SAMPLE_TEXT)
    assert set(result["skills"]) >= {"Python", "Java", "Kafka", "Kubernetes", "PostgreSQL", "AWS"}
    # Never invents a skill that isn't in the text
    assert "Ruby" not in result["skills"]


def test_extracts_labeled_sections_verbatim():
    result = parse_resume(SAMPLE_TEXT)
    assert "IIT Guwahati" in result["education"][0]
    assert "Walmart Global Tech" in result["experience"][0]
    assert "Trip Planner" in result["projects"][0]
    assert "AWS Certified Developer" in result["certifications"][0]


def test_missing_sections_are_empty_not_invented():
    text = "Jordan Lee\njordan@example.com"
    result = parse_resume(text)
    assert result["education"] == []
    assert result["experience"] == []
    assert result["projects"] == []
    assert result["certifications"] == []
    assert result["skills"] == []
