import pytest


async def _publish_and_sync(client, **overrides):
    payload = {
        "title": "Software Engineer Intern",
        "company": "Acme Corp",
        "location": "Remote - India",
        "remote": True,
        "employment_type": "internship",
        "experience_level": "fresher",
        "description": "Backend work with Python and Kafka.",
        "skills": ["Python", "SQL", "Kafka"],
    }
    payload.update(overrides)
    await client.post("/api/mock/jobs", json=payload)
    synced = await client.post("/api/jobs/sync/mock")
    return synced.json()[-1]


@pytest.mark.asyncio
async def test_compute_match_for_job(auth_client):
    job = await _publish_and_sync(auth_client)
    await auth_client.post("/api/profile/skills", json={"name": "Python", "category": "programming_languages"})

    response = await auth_client.post(f"/api/matches/compute/{job['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job["id"]
    assert "Python" in body["matched_skills"]
    assert body["overall_score"] > 0
    assert body["explanation"]


@pytest.mark.asyncio
async def test_compute_match_missing_job_404(auth_client):
    response = await auth_client.post("/api/matches/compute/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_matches_filters_by_min_score(auth_client):
    job1 = await _publish_and_sync(auth_client, title="Great Fit", skills=["Python"])
    job2 = await _publish_and_sync(
        auth_client, title="Poor Fit", skills=["Rust", "Go"], url="https://x/2", external_id="poorfit"
    )
    await auth_client.post("/api/profile/skills", json={"name": "Python", "category": "programming_languages"})

    await auth_client.post(f"/api/matches/compute/{job1['id']}")
    await auth_client.post(f"/api/matches/compute/{job2['id']}")

    all_matches = await auth_client.get("/api/matches")
    assert len(all_matches.json()) == 2
    # sorted descending by score
    scores = [m["overall_score"] for m in all_matches.json()]
    assert scores == sorted(scores, reverse=True)

    high_only = await auth_client.get("/api/matches", params={"min_score": 90})
    assert all(m["overall_score"] >= 90 for m in high_only.json())


@pytest.mark.asyncio
async def test_recompute_match_updates_existing_row_not_duplicate(auth_client):
    job = await _publish_and_sync(auth_client)
    await auth_client.post(f"/api/matches/compute/{job['id']}")
    await auth_client.post("/api/profile/skills", json={"name": "Python", "category": "programming_languages"})
    await auth_client.post(f"/api/matches/compute/{job['id']}")

    listing = await auth_client.get("/api/matches")
    assert len(listing.json()) == 1
    assert "Python" in listing.json()[0]["matched_skills"]


@pytest.mark.asyncio
async def test_compute_all_scores_every_unmatched_job(auth_client):
    await _publish_and_sync(auth_client, title="Job A")
    await _publish_and_sync(auth_client, title="Job B", url="https://x/b", external_id="b")

    response = await auth_client.post("/api/matches/compute-all")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Running again with no new jobs should compute nothing further.
    second = await auth_client.post("/api/matches/compute-all")
    assert second.json() == []


@pytest.mark.asyncio
async def test_matches_scoped_to_owner(client):
    reg_a = await client.post("/api/auth/register", json={"email": "ma@example.com", "password": "supersecret1"})
    token_a = reg_a.json()["access_token"]
    job = await _publish_and_sync_with_token(client, token_a)

    reg_b = await client.post("/api/auth/register", json={"email": "mb@example.com", "password": "supersecret1"})
    token_b = reg_b.json()["access_token"]
    await client.post(
        f"/api/matches/compute/{job['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )

    listing_a = await client.get("/api/matches", headers={"Authorization": f"Bearer {token_a}"})
    assert listing_a.json() == []


async def _publish_and_sync_with_token(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Software Engineer Intern",
        "company": "Acme Corp",
        "skills": ["Python"],
        "url": "https://x/scoped",
        "external_id": "scoped-1",
    }
    await client.post("/api/mock/jobs", json=payload, headers=headers)
    synced = await client.post("/api/jobs/sync/mock", headers=headers)
    return synced.json()[-1]
