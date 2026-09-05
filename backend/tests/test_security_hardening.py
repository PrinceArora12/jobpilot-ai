"""
Phase 12: rate limiting and baseline security response headers.
"""
import pytest


@pytest.mark.asyncio
async def test_responses_carry_baseline_security_headers(client):
    resp = await client.get("/api/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "permissions-policy" in resp.headers
    # Local/test traffic is plain HTTP — HSTS must not be forced here.
    assert "strict-transport-security" not in resp.headers


@pytest.mark.asyncio
async def test_login_is_rate_limited_after_repeated_attempts(client):
    await client.post(
        "/api/auth/register",
        json={"email": "ratelimit-login@example.com", "password": "supersecret1", "first_name": "RL"},
    )

    statuses = []
    for _ in range(25):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "ratelimit-login@example.com", "password": "wrong-password"},
        )
        statuses.append(resp.status_code)

    assert 401 in statuses  # legitimate failed-auth responses still happen
    assert 429 in statuses  # and the limiter eventually kicks in
    assert statuses.index(429) > statuses.index(401)  # only after the budget is used up


@pytest.mark.asyncio
async def test_register_is_rate_limited_after_repeated_attempts(client):
    statuses = []
    for i in range(15):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": f"ratelimit-register-{i}@example.com",
                "password": "supersecret1",
                "first_name": "RL",
            },
        )
        statuses.append(resp.status_code)

    assert 201 in statuses
    assert 429 in statuses
