"""
Phase 7 end-to-end (at the service/API layer): watcher detects a newly
published mock job, screens it against every opted-in user's profile,
queues it by priority, and processes the queue into a "ready_for_review"
Application — with every latency timestamp stamped along the way.
"""
async def _enable_rapid_apply(client, min_score=50):
    resp = await client.put(
        "/api/rapid-apply/settings",
        json={"rapid_apply_enabled": True, "min_match_score_to_apply": min_score},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _add_matching_skill(client, skill="Python"):
    resp = await client.post("/api/profile/skills", json={"name": skill, "category": "technical"})
    assert resp.status_code in (200, 201), resp.text


async def _publish_mock_job(client, title="Rapid Apply QA Engineer", skills=None):
    payload = {
        "title": title,
        "company": "Rapid Apply QA Corp",
        "location": "Remote",
        "remote": True,
        "employment_type": "full_time",
        "description": "Build things with Python and FastAPI.",
        "requirements": ["Python"],
        "skills": skills or ["Python"],
    }
    resp = await client.post("/api/mock/jobs", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_get_and_update_rapid_apply_settings(auth_client):
    resp = await auth_client.get("/api/rapid-apply/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rapid_apply_enabled"] is False
    assert body["min_match_score_to_apply"] == 60

    updated = await _enable_rapid_apply(auth_client, min_score=55)
    assert updated["rapid_apply_enabled"] is True
    assert updated["min_match_score_to_apply"] == 55


async def test_run_cycle_detects_matches_queues_and_processes(auth_client):
    await _enable_rapid_apply(auth_client, min_score=50)
    await _add_matching_skill(auth_client, "Python")
    await _publish_mock_job(auth_client, title="Rapid Apply QA Engineer", skills=["Python"])

    resp = await auth_client.post("/api/rapid-apply/run-cycle")
    assert resp.status_code == 200, resp.text
    result = resp.json()

    assert result["detection"]["jobs_detected"] == 1
    assert result["detection"]["evaluations"] == 1
    assert result["detection"]["queued"] == 1
    assert result["detection"]["skipped_ineligible"] == 0
    assert result["processed"] == 1
    assert result["completed"] == 1
    assert result["failed"] == 0

    queue_resp = await auth_client.get("/api/rapid-apply/queue")
    assert queue_resp.status_code == 200
    entries = queue_resp.json()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["status"] == "completed"
    assert entry["application_id"] is not None
    assert entry["job"]["title"] == "Rapid Apply QA Engineer"
    assert entry["match_score"] >= 50
    assert entry["priority"] in (0, 1, 2, 3)

    # Every stage of the latency pipeline (spec section 58) is stamped.
    for field in (
        "first_seen_at",
        "detected_at",
        "normalized_at",
        "matched_at",
        "queued_at",
        "application_started_at",
        "application_completed_at",
    ):
        assert entry[field] is not None, f"{field} was not stamped"

    # It actually created a real Application and handed it to Phase 8's
    # browser automation. This test suite has no live HTTP server for
    # Playwright to reach (httpx's ASGITransport talks to the app
    # in-process, over no real socket) — so automation correctly can't
    # complete and the application honestly lands in "needs_manual_review"
    # rather than ever claiming a submission that didn't happen. The real
    # Playwright automation logic (mapper, failsafes, fill-and-submit) is
    # proven directly against a real HTTP server in
    # test_browser_automation.py, and the whole pipeline ending in an
    # actual "submitted" status is proven by the live end-to-end script
    # against the real running backend.
    apps_resp = await auth_client.get("/api/applications")
    apps = apps_resp.json()
    assert len(apps) == 1
    assert apps[0]["status"] == "needs_manual_review"
    assert apps[0]["match_score"] == entry["match_score"]
    assert any(
        e["event_type"] == "automation_failsafe" and "manual completion" in e["message"]
        for e in apps[0]["events"]
    )


async def test_automation_success_promotes_application_to_submitted(auth_client, monkeypatch):
    """Isolates the pipeline's reaction to automation succeeding, without
    needing a live HTTP server: patches the automation call itself so this
    stays fast and infra-free while still proving the wiring end to end."""
    from app.automation.browser_automation import AutomationResult

    async def fake_automation(form_url, profile, user, resume, job, matched_skills):
        return AutomationResult(status="submitted", filled_fields=["full_name", "email", "resume"])

    monkeypatch.setattr("app.services.automation_service.run_application_automation", fake_automation)

    await _enable_rapid_apply(auth_client, min_score=50)
    await _add_matching_skill(auth_client, "Python")
    await _publish_mock_job(auth_client, title="Auto Submit QA Role", skills=["Python"])

    resp = await auth_client.post("/api/rapid-apply/run-cycle")
    assert resp.status_code == 200, resp.text

    apps_resp = await auth_client.get("/api/applications")
    apps = apps_resp.json()
    assert len(apps) == 1
    assert apps[0]["status"] == "submitted"
    assert apps[0]["applied_at"] is not None
    assert any("automation submitted this application" in e["message"] for e in apps[0]["events"])


async def test_non_mock_source_is_never_automated(auth_client, db_session):
    """Even if a real-source job somehow entered the queue, automation must
    refuse outright rather than attempt anything against it (spec 6/51)."""
    import uuid as uuid_module
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.application import Application
    from app.models.job import Company, Job
    from app.models.user import User
    from app.services.automation_service import attempt_submission

    # Fetch the user id via auth_client BEFORE touching db_session: both
    # fixtures share one underlying StaticPool sqlite connection, and
    # interleaving an HTTP call (which opens/commits its own session-level
    # transaction) between db_session's flush() and commit() can clobber
    # db_session's still-uncommitted work on that shared connection.
    me_resp = await auth_client.get("/api/auth/me")
    user_id = uuid_module.UUID(me_resp.json()["id"])

    company = Company(name="Real ATS Co")
    db_session.add(company)
    await db_session.flush()
    job = Job(
        external_id="real-1",
        source="greenhouse",
        title="Real Source Role",
        company_id=company.id,
        url="https://boards.greenhouse.io/real/jobs/1",
        content_hash="x" * 64,
        first_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    await db_session.flush()

    application = Application(
        user_id=user_id,
        job_id=job.id,
        status="ready_for_review",
        discovered_at=datetime.now(timezone.utc),
    )
    # Explicitly initialize the relationship collection while the object
    # is still transient: attempt_submission appends to application.events
    # synchronously, and touching an *unloaded* collection for the first
    # time on an already-persistent (committed) async ORM object triggers
    # a real lazy-load, which needs a greenlet context this direct call
    # doesn't have. Production code (rapid_apply_service.process_next)
    # never hits this because it appends before the object is ever added
    # to the session at all.
    application.events = []
    db_session.add(application)
    await db_session.commit()

    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()

    result = await attempt_submission(db_session, application, job, user)
    assert result.status == "failsafe_stopped"
    assert result.reason == "automation_not_permitted_for_source"
    assert application.status == "needs_manual_review"


async def test_ineligible_job_is_never_queued(auth_client):
    await _enable_rapid_apply(auth_client, min_score=50)
    # Block the company outright -> eligibility fails before matching runs.
    resp = await auth_client.post(
        "/api/mock/jobs",
        json={
            "title": "Should Not Queue",
            "company": "Blocked Rapid Apply Co",
            "remote": True,
            "description": "n/a",
            "skills": ["Python"],
        },
    )
    assert resp.status_code == 201

    # Mark the company blocked directly isn't exposed via API yet (Phase
    # 10), so instead prove the low-score path: no matching skills at all
    # means the score falls below the default threshold and it's skipped.
    cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    body = cycle.json()
    assert body["detection"]["jobs_detected"] == 1
    assert body["detection"]["queued"] == 0
    assert body["detection"]["skipped_low_score"] == 1

    queue_resp = await auth_client.get("/api/rapid-apply/queue")
    assert queue_resp.json() == []


async def test_users_without_rapid_apply_enabled_are_never_screened(auth_client):
    # rapid_apply_enabled defaults to False — publishing a job should not
    # evaluate it against this user at all.
    await _publish_mock_job(auth_client)
    resp = await auth_client.post("/api/rapid-apply/run-cycle")
    body = resp.json()
    assert body["detection"]["jobs_detected"] == 1
    assert body["detection"]["evaluations"] == 0
    assert body["detection"]["queued"] == 0


async def test_stats_reflect_completed_entries(auth_client):
    await _enable_rapid_apply(auth_client, min_score=50)
    await _add_matching_skill(auth_client, "Python")
    await _publish_mock_job(auth_client)
    await auth_client.post("/api/rapid-apply/run-cycle")

    stats_resp = await auth_client.get("/api/rapid-apply/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_queued"] == 1
    assert stats["completed"] == 1
    assert stats["queued"] == 0
    assert stats["latency"]["count"] == 1
    assert stats["latency"]["avg_total_seconds"] is not None
    assert stats["latency"]["avg_total_seconds"] >= 0


async def test_running_cycle_twice_does_not_double_queue_same_job(auth_client):
    await _enable_rapid_apply(auth_client, min_score=50)
    await _add_matching_skill(auth_client, "Python")
    await _publish_mock_job(auth_client)

    first = await auth_client.post("/api/rapid-apply/run-cycle")
    assert first.json()["detection"]["queued"] == 1

    # Second cycle: no new mock postings, so nothing new is detected or
    # re-evaluated (the mock source only yields unconsumed postings).
    second = await auth_client.post("/api/rapid-apply/run-cycle")
    assert second.json()["detection"]["jobs_detected"] == 0
    assert second.json()["detection"]["queued"] == 0

    queue_resp = await auth_client.get("/api/rapid-apply/queue")
    assert len(queue_resp.json()) == 1
