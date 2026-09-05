import pytest


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_token(client):
    response = await client.post(
        "/api/auth/register",
        json={"email": "ankita@example.com", "password": "supersecret1", "first_name": "Ankita"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "ankita@example.com"
    assert "hashed_password" not in body["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "supersecret1"}
    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_register_rejects_short_password(client):
    response = await client.post(
        "/api/auth/register", json={"email": "short@example.com", "password": "abc"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post(
        "/api/auth/register", json={"email": "login@example.com", "password": "supersecret1"}
    )
    response = await client.post(
        "/api/auth/login", json={"email": "login@example.com", "password": "supersecret1"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client):
    await client.post(
        "/api/auth/register", json={"email": "wrongpw@example.com", "password": "supersecret1"}
    )
    response = await client.post(
        "/api/auth/login", json={"email": "wrongpw@example.com", "password": "nope-nope-nope"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_rejected(client):
    response = await client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "whatever1"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client):
    register = await client.post(
        "/api/auth/register", json={"email": "me@example.com", "password": "supersecret1"}
    )
    token = register.json()["access_token"]

    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_me_rejects_invalid_token(client):
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer garbage-token"})
    assert response.status_code == 401
