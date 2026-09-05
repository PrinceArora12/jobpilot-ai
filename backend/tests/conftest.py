"""
Test fixtures.

Uses an in-memory SQLite database (via aiosqlite) instead of PostgreSQL so
the suite runs anywhere with no external services — production always uses
PostgreSQL per app/database/session.py and .env.example.
"""
import os

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.redis_client import get_redis
from app.database.session import Base, get_db
from app.main import app
from app.services.priority_queue import RedisPriorityQueue

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
async def _prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _clean_rapid_apply_redis():
    """Rapid Apply (Phase 7) uses the real local Redis instance (matching
    production, unlike the in-memory-SQLite DB) — flush its default queue
    namespace before and after every test so tests never see leftover
    entries from one another."""
    queue = RedisPriorityQueue(get_redis(), namespace="default")
    await queue.clear()
    yield
    await queue.clear()


@pytest_asyncio.fixture(autouse=True)
async def _clean_rate_limit_counters():
    """Phase 12's rate limiter (app/core/rate_limit.py) also uses the real
    local Redis instance, keyed by client IP — which httpx's ASGITransport
    reports the same way for every test. Without resetting these counters,
    unrelated tests would share one budget and later ones could start
    failing with 429s that have nothing to do with what they're testing."""
    redis_client = get_redis()

    async def _flush():
        keys = await redis_client.keys("ratelimit:*")
        if keys:
            await redis_client.delete(*keys)

    await _flush()
    yield
    await _flush()


@pytest_asyncio.fixture
async def auth_client(client):
    """An AsyncClient pre-authenticated as a freshly registered user."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": "fixture-user@example.com", "password": "supersecret1", "first_name": "Fix"},
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
