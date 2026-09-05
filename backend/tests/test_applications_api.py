import pytest


async def _publish_and_sync(client, **overrides):
    payload = {
        "title": "Software Engineer Intern",
        "company": "Acme Corp",
        "skills": ["Python"],
    }
    payload.update(overrides)
    await client.post("/api/mock/jobs", json=payload)
    synced = await client.post("/api/jobs/sync/mock")
    return synced.json()[-1]


@pytest.mark.asyncio
async def test_create_application_tracks_job(auth_client):
    job = await _publish_and_sync(auth_client)
    response = await auth_client.post("/api/applications", json={"job_id": job["id"]})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "discovered"
    assert body["job"]["id"] == job["id"]
    assert len(body["events"]) == 1
    assert body["events"][0]["event_type"] == "status_changed"


@pytest.mark.asyncio
async def test_create_application_captures_existing_match_score(auth_client):
    job = await _publish_and_sync(auth_client)
    await auth_client.post("/api/profile/skills", json={"name": "Python", "category": "programming_languages"})
    await auth_client.post(f"/api/matches/compute/{job['id']}")

    response = await auth_client.post("/api/applications", json={"job_id": job["id"]})
    assert response.json()["match_score"] is not None


@pytest.mark.asyncio
async def test_duplicate_application_rejected(auth_client):
    job = await _publish_and_sync(auth_client)
    await auth_client.post("/api/applications", json={"job_id": job["id"]})
    dupe = await auth_client.post("/api/applications", json={"job_id": job["id"]})
    assert dupe.status_code == 409


@pytest.mark.asyncio
async def test_invalid_status_rejected(auth_client):
    job = await _publish_and_sync(auth_client)
    response = await auth_client.post(
        "/api/applications", json={"job_id": job["id"], "status": "not-a-real-status"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_status_transition_logs_event_and_sets_applied_at(auth_client):
    job = await _publish_and_sync(auth_client)
    created = await auth_client.post("/api/applications", json={"job_id": job["id"]})
    app_id = created.json()["id"]

    updated = await auth_client.put(f"/api/applications/{app_id}", json={"status": "submitted"})
    body = updated.json()
    assert body["status"] == "submitted"
    assert body["applied_at"] is not None
    assert any(e["event_type"] == "status_changed" and "submitted" in e["message"] for e in body["events"])


@pytest.mark.asyncio
async def test_add_note_appends_event(auth_client):
    job = await _publish_and_sync(auth_client)
    created = await auth_client.post("/api/applications", json={"job_id": job["id"]})
    app_id = created.json()["id"]

    noted = await auth_client.post(f"/api/applications/{app_id}/notes", json={"message": "Followed up via email"})
    assert any(e["event_type"] == "note" and e["message"] == "Followed up via email" for e in noted.json()["events"])


@pytest.mark.asyncio
async def test_list_and_filter_applications_by_status(auth_client):
    job1 = await _publish_and_sync(auth_client, title="Job A")
    job2 = await _publish_and_sync(auth_client, title="Job B", url="https://x/2", external_id="b")
    a1 = await auth_client.post("/api/applications", json={"job_id": job1["id"]})
    await auth_client.post("/api/applications", json={"job_id": job2["id"]})
    await auth_client.put(f"/api/applications/{a1.json()['id']}", json={"status": "interview"})

    all_apps = await auth_client.get("/api/applications")
    assert len(all_apps.json()) == 2

    interviews = await auth_client.get("/api/applications", params={"status": "interview"})
    assert len(interviews.json()) == 1
    assert interviews.json()[0]["job"]["title"] == "Job A"


@pytest.mark.asyncio
async def test_delete_application(auth_client):
    job = await _publish_and_sync(auth_client)
    created = await auth_client.post("/api/applications", json={"job_id": job["id"]})
    app_id = created.json()["id"]

    deleted = await auth_client.delete(f"/api/applications/{app_id}")
    assert deleted.status_code == 204

    fetch = await auth_client.get(f"/api/applications/{app_id}")
    assert fetch.status_code == 404


@pytest.mark.asyncio
async def test_applications_scoped_to_owner(client):
    reg_a = await client.post("/api/auth/register", json={"email": "aa@example.com", "password": "supersecret1"})
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    await client.post("/api/mock/jobs", json={"title": "X", "company": "Y", "url": "https://x/1", "external_id": "1"}, headers=headers_a)
    synced = await client.post("/api/jobs/sync/mock", headers=headers_a)
    job_id = synced.json()[0]["id"]
    created = await client.post("/api/applications", json={"job_id": job_id}, headers=headers_a)
    app_id = created.json()["id"]

    reg_b = await client.post("/api/auth/register", json={"email": "bb@example.com", "password": "supersecret1"})
    token_b = reg_b.json()["access_token"]
    fetch_b = await client.get(f"/api/applications/{app_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert fetch_b.status_code == 404
