"""API-level tests for the AI Application Assistant (Phase 9): question
answering and resume tailoring preview/apply."""


async def _create_job_and_application(client, title="Assistant QA Role", skills=None):
    resp = await client.post(
        "/api/mock/jobs",
        json={
            "title": title,
            "company": "Assistant QA Co",
            "remote": True,
            "description": "A role.",
            "skills": skills or ["Python"],
        },
    )
    assert resp.status_code == 201
    sync_resp = await client.post("/api/jobs/sync/mock")
    assert sync_resp.status_code == 200
    job = next(j for j in sync_resp.json() if j["title"] == title)

    app_resp = await client.post("/api/applications", json={"job_id": job["id"]})
    assert app_resp.status_code == 201
    return job, app_resp.json()


async def test_answer_grounded_skill_question(auth_client):
    await auth_client.post("/api/profile/skills", json={"name": "Python", "category": "technical"})
    _job, application = await _create_job_and_application(auth_client)

    resp = await auth_client.post(
        "/api/assistant/answer",
        json={"application_id": application["id"], "question": "Do you have experience with Python?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "answered"
    assert body["source"] == "profile.skills"
    assert body["confidence"] > 0.8


async def test_answer_unsupported_question_returns_needs_user_input(auth_client):
    _job, application = await _create_job_and_application(auth_client)

    resp = await auth_client.post(
        "/api/assistant/answer",
        json={"application_id": application["id"], "question": "What is your notice period?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "needs_user_input"
    assert body["answer"] is None
    assert body["reason"]


async def test_answer_requires_owned_application(auth_client):
    resp = await auth_client.post(
        "/api/assistant/answer",
        json={"application_id": "00000000-0000-0000-0000-000000000000", "question": "Python experience?"},
    )
    assert resp.status_code == 404


async def _upload_resume_with_skills(client, skills):
    files = {"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")}
    resp = await client.post("/api/resumes", files=files, data={"label": "Main"})
    assert resp.status_code == 201
    resume = resp.json()
    # parsed_data starts empty for a bogus PDF — set skills directly via the
    # resume update endpoint so the tailoring tests have something to reorder.
    update_resp = await client.put(
        f"/api/resumes/{resume['id']}", json={"parsed_data": {"skills": skills}}
    )
    assert update_resp.status_code == 200
    return update_resp.json()


async def test_tailor_preview_reorders_matched_skills_first(auth_client):
    resume = await _upload_resume_with_skills(auth_client, ["Django", "Python", "Docker"])
    job, _application = await _create_job_and_application(
        auth_client, title="Tailor Preview Role", skills=["Docker", "Python"]
    )

    resp = await auth_client.post(
        "/api/assistant/tailor-resume/preview", json={"resume_id": resume["id"], "job_id": job["id"]}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["original_order"] == ["Django", "Python", "Docker"]
    assert body["suggested_order"] == ["Python", "Docker", "Django"]
    assert set(body["matched_keywords"]) == {"Python", "Docker"}
    assert body["changed"] is True
    # Never fabricates or drops a skill — same multiset, different order.
    assert sorted(body["original_order"]) == sorted(body["suggested_order"])


async def test_tailor_apply_persists_approved_order(auth_client):
    resume = await _upload_resume_with_skills(auth_client, ["Django", "Python", "Docker"])

    resp = await auth_client.post(
        "/api/assistant/tailor-resume/apply",
        json={"resume_id": resume["id"], "skill_order": ["Python", "Docker", "Django"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["parsed_data"]["skills"] == ["Python", "Docker", "Django"]

    get_resp = await auth_client.get(f"/api/resumes/{resume['id']}")
    assert get_resp.json()["parsed_data"]["skills"] == ["Python", "Docker", "Django"]


async def test_tailor_apply_rejects_added_or_removed_skills(auth_client):
    resume = await _upload_resume_with_skills(auth_client, ["Django", "Python"])

    resp = await auth_client.post(
        "/api/assistant/tailor-resume/apply",
        json={"resume_id": resume["id"], "skill_order": ["Python", "Kubernetes"]},
    )
    assert resp.status_code == 400
    assert "same skills" in resp.json()["detail"]
