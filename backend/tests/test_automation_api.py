"""
Phase 10 end-to-end (at the service/API layer): automation rules (limits +
blocklists), the running/paused/stopped kill switch, and the in-app
notification feed — spec sections 60-62.

Every enforcement check lives in app/services/automation_rules_service.py
and is gated through screening_block_reason, which
rapid_apply_service.detect_and_enqueue calls per (user, job) pair *before*
matching ever runs — these tests prove that gate from the API layer down,
the same way test_rapid_apply_api.py proves the rest of the pipeline.
"""
async def _enable_rapid_apply(client, min_score=0):
    resp = await client.put(
        "/api/rapid-apply/settings",
        json={"rapid_apply_enabled": True, "min_match_score_to_apply": min_score},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _add_matching_skill(client, skill="Python"):
    resp = await client.post("/api/profile/skills", json={"name": skill, "category": "technical"})
    assert resp.status_code in (200, 201), resp.text


async def _publish_mock_job(client, title="Automation QA Role", company="Automation QA Corp", skills=None):
    payload = {
        "title": title,
        "company": company,
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


# ---------------------------------------------------------------------------
# Rule CRUD + state transitions
# ---------------------------------------------------------------------------


async def test_get_rules_lazily_creates_defaults(auth_client):
    resp = await auth_client.get("/api/automation/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "running"
    assert body["max_applications_per_hour"] is None
    assert body["max_applications_per_day"] is None
    assert body["max_applications_per_company"] is None
    assert body["blocked_sources"] == []
    assert body["blocked_companies"] == []
    assert body["blocked_keywords"] == []


async def test_update_rules_persists_limits_and_blocklists(auth_client):
    resp = await auth_client.put(
        "/api/automation/rules",
        json={
            "max_applications_per_day": 5,
            "blocked_companies": ["Bad Co"],
            "blocked_keywords": ["unpaid"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["max_applications_per_day"] == 5
    assert body["blocked_companies"] == ["Bad Co"]
    assert body["blocked_keywords"] == ["unpaid"]
    # Untouched fields keep their defaults.
    assert body["max_applications_per_hour"] is None

    # And it round-trips on a fresh GET.
    again = await auth_client.get("/api/automation/rules")
    assert again.json()["max_applications_per_day"] == 5


async def test_update_rules_rejects_non_positive_limits(auth_client):
    resp = await auth_client.put("/api/automation/rules", json={"max_applications_per_hour": 0})
    assert resp.status_code == 422


async def test_start_pause_stop_transition_state(auth_client):
    paused = await auth_client.post("/api/automation/pause")
    assert paused.json()["state"] == "paused"

    stopped = await auth_client.post("/api/automation/stop")
    assert stopped.json()["state"] == "stopped"

    started = await auth_client.post("/api/automation/start")
    assert started.json()["state"] == "running"


# ---------------------------------------------------------------------------
# Enforcement: state, blocklists, rate limits — all gate BEFORE queueing.
# ---------------------------------------------------------------------------


async def test_stopped_automation_blocks_all_queueing(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await auth_client.post("/api/automation/stop")
    await _publish_mock_job(auth_client)

    cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    body = cycle.json()
    assert body["detection"]["jobs_detected"] == 1
    assert body["detection"]["queued"] == 0
    assert body["detection"]["skipped_by_automation_rules"] == 1

    queue_resp = await auth_client.get("/api/rapid-apply/queue")
    assert queue_resp.json() == []


async def test_paused_automation_blocks_queueing(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await auth_client.post("/api/automation/pause")
    await _publish_mock_job(auth_client)

    cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    assert cycle.json()["detection"]["skipped_by_automation_rules"] == 1


async def test_blocked_source_prevents_queueing(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await auth_client.put("/api/automation/rules", json={"blocked_sources": ["mock"]})
    await _publish_mock_job(auth_client)

    cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    body = cycle.json()
    assert body["detection"]["queued"] == 0
    assert body["detection"]["skipped_by_automation_rules"] == 1


async def test_blocked_company_prevents_queueing(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await auth_client.put("/api/automation/rules", json={"blocked_companies": ["Blocklisted Inc"]})
    await _publish_mock_job(auth_client, company="Blocklisted Inc")

    cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    body = cycle.json()
    assert body["detection"]["queued"] == 0
    assert body["detection"]["skipped_by_automation_rules"] == 1


async def test_blocked_keyword_prevents_queueing(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await auth_client.put("/api/automation/rules", json={"blocked_keywords": ["fastapi"]})
    await _publish_mock_job(auth_client, title="Role mentioning FastAPI")

    cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    body = cycle.json()
    assert body["detection"]["queued"] == 0
    assert body["detection"]["skipped_by_automation_rules"] == 1


async def test_daily_rate_limit_stops_further_queueing_and_notifies(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await auth_client.put("/api/automation/rules", json={"max_applications_per_day": 1})

    await _publish_mock_job(auth_client, title="First Role", company="Rate Ltd A")
    first_cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    assert first_cycle.json()["detection"]["queued"] == 1

    await _publish_mock_job(auth_client, title="Second Role", company="Rate Ltd B")
    second_cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    body = second_cycle.json()
    assert body["detection"]["queued"] == 0
    assert body["detection"]["skipped_by_automation_rules"] == 1

    # A rate-limit notification should have been raised exactly once.
    notes = await auth_client.get("/api/notifications")
    rate_limit_notes = [n for n in notes.json() if n["type"] == "rate_limit_reached"]
    assert len(rate_limit_notes) == 1


async def test_per_company_rate_limit_enforced(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await auth_client.put("/api/automation/rules", json={"max_applications_per_company": 1})

    await _publish_mock_job(auth_client, title="Role One", company="Same Co")
    first_cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    assert first_cycle.json()["detection"]["queued"] == 1

    await _publish_mock_job(auth_client, title="Role Two", company="Same Co")
    second_cycle = await auth_client.post("/api/rapid-apply/run-cycle")
    body = second_cycle.json()
    assert body["detection"]["queued"] == 0
    assert body["detection"]["skipped_by_automation_rules"] == 1


# ---------------------------------------------------------------------------
# Notifications feed
# ---------------------------------------------------------------------------


async def test_notification_created_on_application_outcome(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await _publish_mock_job(auth_client)

    await auth_client.post("/api/rapid-apply/run-cycle")

    resp = await auth_client.get("/api/notifications")
    assert resp.status_code == 200
    notifications = resp.json()
    assert len(notifications) >= 1
    assert all(n["is_read"] is False for n in notifications)


async def test_unread_count_and_mark_read(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await _publish_mock_job(auth_client)
    await auth_client.post("/api/rapid-apply/run-cycle")

    unread_before = await auth_client.get("/api/notifications/unread-count")
    assert unread_before.json()["unread_count"] >= 1

    notes = (await auth_client.get("/api/notifications")).json()
    first_id = notes[0]["id"]

    read_resp = await auth_client.post(f"/api/notifications/{first_id}/read")
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    all_read = await auth_client.post("/api/notifications/read-all")
    assert all_read.status_code == 200

    unread_after = await auth_client.get("/api/notifications/unread-count")
    assert unread_after.json()["unread_count"] == 0


async def test_unread_only_filter(auth_client):
    await _enable_rapid_apply(auth_client)
    await _add_matching_skill(auth_client)
    await _publish_mock_job(auth_client)
    await auth_client.post("/api/rapid-apply/run-cycle")

    await auth_client.post("/api/notifications/read-all")
    unread_resp = await auth_client.get("/api/notifications", params={"unread_only": True})
    assert unread_resp.json() == []
