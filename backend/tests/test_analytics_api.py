"""
Phase 11: analytics (funnel, conversion rates, resume performance,
timeline). The funnel is built from ApplicationEvent history rather than
an application's current status alone, so these tests specifically prove
that an application which passed through "interview" before ending in
"rejected" still counts as having reached the interview stage.
"""
import io

import pytest


async def _publish_and_sync(client, **overrides):
    payload = {
        "title": "Analytics QA Role",
        "company": "Analytics QA Corp",
        "skills": ["Python"],
    }
    payload.update(overrides)
    await client.post("/api/mock/jobs", json=payload)
    synced = await client.post("/api/jobs/sync/mock")
    return synced.json()[-1]


async def _create_application(client, title="Analytics QA Role", company="Analytics QA Corp"):
    job = await _publish_and_sync(client, title=title, company=company)
    resp = await client.post("/api/applications", json={"job_id": job["id"]})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _advance_status(client, application_id, status_value):
    resp = await client.put(f"/api/applications/{application_id}", json={"status": status_value})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_summary_and_funnel_are_zero_with_no_applications(auth_client):
    summary = await auth_client.get("/api/analytics/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_applications"] == 0
    assert body["total_submitted"] == 0
    assert body["avg_match_score"] is None
    assert body["avg_days_to_submit"] is None

    funnel = await auth_client.get("/api/analytics/funnel")
    fbody = funnel.json()
    assert fbody["total_applications"] == 0
    assert all(stage["count"] == 0 for stage in fbody["stages"])
    assert fbody["submitted_rate"] is None


@pytest.mark.asyncio
async def test_funnel_counts_full_lifecycle_progress(auth_client):
    app1 = await _create_application(auth_client)
    await _advance_status(auth_client, app1["id"], "matched")
    await _advance_status(auth_client, app1["id"], "saved")
    await _advance_status(auth_client, app1["id"], "preparing")
    await _advance_status(auth_client, app1["id"], "ready_for_review")
    await _advance_status(auth_client, app1["id"], "submitted")
    await _advance_status(auth_client, app1["id"], "interview")
    await _advance_status(auth_client, app1["id"], "offer")

    funnel = (await auth_client.get("/api/analytics/funnel")).json()
    stage_counts = {s["name"]: s["count"] for s in funnel["stages"]}
    assert stage_counts["discovered"] == 1
    assert stage_counts["matched"] == 1
    assert stage_counts["saved"] == 1
    assert stage_counts["preparing"] == 1
    assert stage_counts["ready_for_review"] == 1
    assert stage_counts["submitted"] == 1
    assert stage_counts["interview"] == 1
    assert stage_counts["offer"] == 1
    assert funnel["submitted_rate"] == 100.0
    assert funnel["interview_rate"] == 100.0
    assert funnel["offer_rate"] == 100.0


@pytest.mark.asyncio
async def test_funnel_credits_stages_reached_before_a_later_rejection(auth_client):
    """An application that reached "interview" and was THEN rejected must
    still count as having reached the interview stage — the funnel
    measures how far an application got, not how it ended."""
    app1 = await _create_application(auth_client)
    await _advance_status(auth_client, app1["id"], "submitted")
    await _advance_status(auth_client, app1["id"], "interview")
    await _advance_status(auth_client, app1["id"], "rejected")

    funnel = (await auth_client.get("/api/analytics/funnel")).json()
    stage_counts = {s["name"]: s["count"] for s in funnel["stages"]}
    assert stage_counts["interview"] == 1
    assert stage_counts["submitted"] == 1
    # "rejected" isn't a funnel stage itself, but its predecessors are credited.
    assert funnel["response_rate"] == 100.0


@pytest.mark.asyncio
async def test_needs_manual_review_counts_toward_submitted_stage(auth_client):
    """Phase 8's honest failsafe outcome still represents a fully prepared
    application, so it must count toward "reached submission" even though
    its literal status string isn't "submitted"."""
    app1 = await _create_application(auth_client)
    await _advance_status(auth_client, app1["id"], "needs_manual_review")

    funnel = (await auth_client.get("/api/analytics/funnel")).json()
    stage_counts = {s["name"]: s["count"] for s in funnel["stages"]}
    assert stage_counts["submitted"] == 1


@pytest.mark.asyncio
async def test_summary_reflects_totals_and_avg_days_to_submit(auth_client):
    app1 = await _create_application(auth_client)
    await _advance_status(auth_client, app1["id"], "submitted")
    await _advance_status(auth_client, app1["id"], "interview")
    await _advance_status(auth_client, app1["id"], "offer")

    app2 = await _create_application(auth_client, title="Analytics QA Role Two", company="Analytics QA Corp Two")
    await _advance_status(auth_client, app2["id"], "submitted")

    summary = (await auth_client.get("/api/analytics/summary")).json()
    assert summary["total_applications"] == 2
    assert summary["total_submitted"] == 2
    assert summary["total_interviews"] == 1
    assert summary["total_offers"] == 1
    assert summary["avg_days_to_submit"] is not None
    assert summary["avg_days_to_submit"] >= 0


@pytest.mark.asyncio
async def test_timeline_reflects_discovered_and_submitted_counts(auth_client):
    app1 = await _create_application(auth_client)
    await _advance_status(auth_client, app1["id"], "submitted")

    timeline = (await auth_client.get("/api/analytics/timeline", params={"days": 7})).json()
    assert len(timeline) == 7
    todays_totals = {"discovered": 0, "submitted": 0}
    for point in timeline:
        todays_totals["discovered"] += point["discovered"]
        todays_totals["submitted"] += point["submitted"]
    assert todays_totals["discovered"] == 1
    assert todays_totals["submitted"] == 1


@pytest.mark.asyncio
async def test_resume_performance_groups_and_ranks_by_resume(auth_client):
    resume_resp = await auth_client.post(
        "/api/resumes?label=Primary%20Resume",
        files={"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake resume content"), "application/pdf")},
    )
    assert resume_resp.status_code == 201, resume_resp.text
    resume_id = resume_resp.json()["id"]

    job = await _publish_and_sync(auth_client, title="Resume Perf Role", company="Resume Perf Corp")
    app_resp = await auth_client.post(
        "/api/applications", json={"job_id": job["id"], "resume_id": resume_id}
    )
    assert app_resp.status_code == 201, app_resp.text
    application = app_resp.json()
    await _advance_status(auth_client, application["id"], "submitted")
    await _advance_status(auth_client, application["id"], "interview")

    performance = (await auth_client.get("/api/analytics/resume-performance")).json()
    assert len(performance) == 1
    entry = performance[0]
    assert entry["resume_id"] == resume_id
    assert entry["label"] == "Primary Resume"
    assert entry["total_applications"] == 1
    assert entry["submitted"] == 1
    assert entry["interviews"] == 1
    assert entry["response_rate"] == 100.0


@pytest.mark.asyncio
async def test_applications_without_a_resume_are_excluded_from_resume_performance(auth_client):
    await _create_application(auth_client)
    performance = (await auth_client.get("/api/analytics/resume-performance")).json()
    assert performance == []
