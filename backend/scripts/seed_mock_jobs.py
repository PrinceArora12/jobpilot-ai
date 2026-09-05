"""
Populates the mock job board with a handful of realistic postings so a
fresh install has something to search/match/apply against.
"""
import asyncio
import os
import sys

import httpx

BASE_URL = os.environ.get("SEED_BASE_URL", "http://localhost:8000/api")

MOCK_JOBS = [
    {
        "title": "Backend Engineer (Python)",
        "company": "Acme Cloud",
        "location": "Bengaluru, India",
        "remote": True,
        "employment_type": "full_time",
        "experience_level": "mid",
        "salary": "\u20b918L - \u20b928L",
        "description": "Build and scale our core API services in Python/FastAPI.",
        "requirements": ["3+ years backend experience", "Strong SQL skills"],
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    },
    {
        "title": "Senior Frontend Engineer (React)",
        "company": "Northwind Retail",
        "location": "Remote",
        "remote": True,
        "employment_type": "full_time",
        "experience_level": "senior",
        "salary": "$130k - $160k",
        "description": "Own our customer-facing React/TypeScript storefront.",
        "requirements": ["5+ years frontend experience", "React + TypeScript"],
        "skills": ["React", "TypeScript", "TailwindCSS"],
    },
    {
        "title": "DevOps Engineer",
        "company": "Skyline Systems",
        "location": "Hyderabad, India",
        "remote": False,
        "employment_type": "full_time",
        "experience_level": "mid",
        "salary": "\u20b920L - \u20b932L",
        "description": "Own CI/CD, Kubernetes clusters, and cloud infra reliability.",
        "requirements": ["Kubernetes", "Terraform", "AWS or Azure"],
        "skills": ["Kubernetes", "Terraform", "AWS", "CI/CD"],
    },
    {
        "title": "Data Scientist",
        "company": "Lumen Analytics",
        "location": "Remote",
        "remote": True,
        "employment_type": "full_time",
        "experience_level": "mid",
        "salary": "$110k - $145k",
        "description": "Build ML models for demand forecasting and pricing.",
        "requirements": ["Python", "Pandas", "ML fundamentals"],
        "skills": ["Python", "Machine Learning", "SQL", "Pandas"],
    },
    {
        "title": "Engineering Manager, Platform",
        "company": "Acme Cloud",
        "location": "Bengaluru, India",
        "remote": False,
        "employment_type": "full_time",
        "experience_level": "lead",
        "salary": "\u20b945L - \u20b965L",
        "description": "Lead a team of 6-8 engineers on our core platform.",
        "requirements": ["8+ years experience", "2+ years managing engineers"],
        "skills": ["Leadership", "Java", "Kafka", "Kubernetes"],
    },
    {
        "title": "QA Automation Engineer",
        "company": "Northwind Retail",
        "location": "Pune, India",
        "remote": True,
        "employment_type": "contract",
        "experience_level": "mid",
        "salary": "\u20b912L - \u20b918L",
        "description": "Build and maintain our Playwright/Cypress e2e suite.",
        "requirements": ["Playwright or Cypress", "CI pipelines"],
        "skills": ["Playwright", "TypeScript", "CI/CD"],
    },
    {
        "title": "Product Manager, Growth",
        "company": "Lumen Analytics",
        "location": "Remote",
        "remote": True,
        "employment_type": "full_time",
        "experience_level": "senior",
        "salary": "$120k - $150k",
        "description": "Own the growth funnel from signup to activation.",
        "requirements": ["4+ years PM experience", "Analytics-driven"],
        "skills": ["Product Management", "SQL", "A/B Testing"],
    },
    {
        "title": "Software Engineering Intern",
        "company": "Skyline Systems",
        "location": "Remote",
        "remote": True,
        "employment_type": "internship",
        "experience_level": "entry",
        "salary": "\u20b940k/month",
        "description": "6-month internship building internal tools.",
        "requirements": ["CS fundamentals", "Any backend language"],
        "skills": ["Python", "Git", "SQL"],
    },
]


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        print(f"Posting {len(MOCK_JOBS)} mock jobs to {BASE_URL}/mock/jobs ...")
        for job in MOCK_JOBS:
            resp = await client.post("/mock/jobs", json=job)
            resp.raise_for_status()
            print(f"  + {job['title']} @ {job['company']}")
    print("Done. They'll appear in search within ~60s, or click 'Sync sources' on the Jobs page now.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.HTTPStatusError as exc:
        print(f"Request failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        sys.exit(1)