"""
Phase 12: account-wide audit log (spec section 52). Every auth event,
application status change, automation rule/state change, and resume
deletion writes one row; GET /audit-log returns only the caller's own rows,
newest first.
"""
import io

import pytest


@pytest.mark.asyncio
async def test_register_and_login_are_logged(client):
    reg = await client.post(
        "/api/auth/register",
        json={"email": "audit-user@example.com", "password": "supersecret1", "first_name": "Audit"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    log = (await client.get("/api/audit-log")).json()
    actions = [entry["action"] for entry in log]
    assert "auth.register" in actions

    await client.post(
        "/api/auth/login", json={"email": "audit-user@example.com", "password": "supersecret1"}
    )
    log2 = (await client.get("/api/audit-log")).json()
    assert "auth.login_success" in [e["action"] for e in log2]


@pytest.mark.asyncio
async def test_failed_login_is_logged_and_visible_once_authenticated(client):
    await client.post(
        "/api/auth/register",
        json={"email": "audit-fail@example.com", "password": "supersecret1", "first_name": "Audit"},
    )
    bad = await client.post(
        "/api/auth/login", json={"email": "audit-fail@example.com", "password": "wrong-password"}
    )
    assert bad.status_code == 401

    login = await client.post(
        "/api/auth/login", json={"email": "audit-fail@example.com", "password": "supersecret1"}
    )
    token = login.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    log = (await client.get("/api/audit-log")).json()
    actions = [e["action"] for e in log]
    assert "auth.login_failed" in actions
    assert "auth.login_success" in actions


@pytest.mark.asyncio
async def test_application_status_change_is_logged(auth_client):
    await auth_client.post("/api/mock/jobs", json={"title": "Audit Role", "company": "Audit Corp", "skills": ["Python"]})
    synced = await auth_client.post("/api/jobs/sync/mock")
    job = synced.json()[-1]

    app_resp = await auth_client.post("/api/applications", json={"job_id": job["id"]})
    application_id = app_resp.json()["id"]

    await auth_client.put(f"/api/applications/{application_id}", json={"status": "matched"})

    log = (await auth_client.get("/api/audit-log")).json()
    matching = [e for e in log if e["action"] == "application.status_changed"]
    assert len(matching) == 1
    assert "discovered -> matched" in matching[0]["detail"]


@pytest.mark.asyncio
async def test_automation_state_and_rule_changes_are_logged(auth_client):
    await auth_client.post("/api/automation/pause")
    await auth_client.post("/api/automation/stop")
    await auth_client.put("/api/automation/rules", json={"max_applications_per_day": 3})

    log = (await auth_client.get("/api/audit-log")).json()
    actions = [e["action"] for e in log]
    assert actions.count("automation.state_changed") == 2
    assert "automation.rules_updated" in actions


@pytest.mark.asyncio
async def test_resume_deletion_is_logged(auth_client):
    resp = await auth_client.post(
        "/api/resumes",
        files={"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake resume content"), "application/pdf")},
    )
    resume_id = resp.json()["id"]
    await auth_client.delete(f"/api/resumes/{resume_id}")

    log = (await auth_client.get("/api/audit-log")).json()
    assert any(e["action"] == "resume.deleted" and resume_id in e["detail"] for e in log)


@pytest.mark.asyncio
async def test_audit_log_is_scoped_to_the_caller(client):
    reg1 = await client.post(
        "/api/auth/register",
        json={"email": "audit-a@example.com", "password": "supersecret1", "first_name": "A"},
    )
    token1 = reg1.json()["access_token"]

    reg2 = await client.post(
        "/api/auth/register",
        json={"email": "audit-b@example.com", "password": "supersecret1", "first_name": "B"},
    )
    token2 = reg2.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {token1}"
    log1 = (await client.get("/api/audit-log")).json()
    assert all("audit-a@example.com" not in (e["detail"] or "") or e["action"] == "auth.register" for e in log1)
    assert len(log1) == 1  # only this user's own register event

    client.headers["Authorization"] = f"Bearer {token2}"
    log2 = (await client.get("/api/audit-log")).json()
    assert len(log2) == 1
    assert log2[0]["action"] == "auth.register"
