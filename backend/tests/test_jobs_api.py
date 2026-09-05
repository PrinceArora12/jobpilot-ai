import pytest


async def _publish_mock_job(client, **overrides):
    payload = {
        "title": "Software Engineer Intern",
        "company": "Acme Corp",
        "location": "Remote - India",
        "remote": True,
        "employment_type": "internship",
        "experience_level": "fresher",
        "salary": "₹40,000/month",
        "description": "Work on backend services using Python and Kafka.",
        "requirements": ["Python", "SQL"],
        "skills": ["Python", "SQL", "Kafka"],
    }
    payload.update(overrides)
    return await client.post("/api/mock/jobs", json=payload)


@pytest.mark.asyncio
async def test_publish_mock_job(client):
    response = await _publish_mock_job(client)
    assert response.status_code == 201
    assert response.json()["consumed_at"] is None


@pytest.mark.asyncio
async def test_sync_mock_ingests_and_dedupes(auth_client):
    await _publish_mock_job(auth_client)
    sync1 = await auth_client.post("/api/jobs/sync/mock")
    assert sync1.status_code == 200
    assert len(sync1.json()) == 1
    job_id = sync1.json()[0]["id"]

    # Publishing nothing new: second sync should find no unconsumed postings
    sync2 = await auth_client.post("/api/jobs/sync/mock")
    assert sync2.json() == []

    listing = await auth_client.get("/api/jobs")
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == job_id
    assert listing.json()["items"][0]["company"]["name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_duplicate_job_same_url_not_double_counted(auth_client):
    await _publish_mock_job(auth_client, url="https://acme.example/jobs/42", external_id="ext-42")
    await auth_client.post("/api/jobs/sync/mock")
    await _publish_mock_job(auth_client, url="https://acme.example/jobs/42", external_id="ext-42")
    await auth_client.post("/api/jobs/sync/mock")

    listing = await auth_client.get("/api/jobs")
    assert listing.json()["total"] == 1


@pytest.mark.asyncio
async def test_search_and_filter_jobs(auth_client):
    await _publish_mock_job(auth_client, title="Backend Engineer Intern", employment_type="internship")
    await _publish_mock_job(
        auth_client,
        title="Senior Data Scientist",
        company="DataCo",
        employment_type="full_time",
        remote=False,
        location="Bengaluru",
        url="https://dataco.example/jobs/1",
        description="Analyze large datasets and build dashboards.",
    )
    await auth_client.post("/api/jobs/sync/mock")

    all_jobs = await auth_client.get("/api/jobs")
    assert all_jobs.json()["total"] == 2

    filtered = await auth_client.get("/api/jobs", params={"employment_type": "full_time"})
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["title"] == "Senior Data Scientist"

    searched = await auth_client.get("/api/jobs", params={"q": "backend"})
    assert searched.json()["total"] == 1

    remote_only = await auth_client.get("/api/jobs", params={"remote": True})
    assert remote_only.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_job_detail(auth_client):
    await _publish_mock_job(auth_client)
    await auth_client.post("/api/jobs/sync/mock")
    listing = await auth_client.get("/api/jobs")
    job_id = listing.json()["items"][0]["id"]

    detail = await auth_client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["skills"] == ["Python", "SQL", "Kafka"]


@pytest.mark.asyncio
async def test_jobs_require_auth(client):
    response = await client.get("/api/jobs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mock_jobs_without_external_id_get_distinct_urls(auth_client):
    """Regression test: two postings that both omit external_id/url must
    not collapse into a single generated URL (they previously both fell
    back to '.../None' and deduped against each other)."""
    await _publish_mock_job(auth_client, title="Job One", url=None, external_id=None)
    await _publish_mock_job(auth_client, title="Job Two", url=None, external_id=None)
    synced = await auth_client.post("/api/jobs/sync/mock")
    assert len(synced.json()) == 2
    urls = {job["url"] for job in synced.json()}
    assert len(urls) == 2
    assert "None" not in "".join(urls)

    listing = await auth_client.get("/api/jobs")
    assert listing.json()["total"] == 2
