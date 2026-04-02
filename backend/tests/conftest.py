"""
Shared pytest fixtures.

Uses a real PostgreSQL test database (requires pgvector extension).
Set TEST_DATABASE_URL to point at a different DB:
  postgresql+asyncpg://jobscraper:jobscraper@localhost:5432/jobscraper_test

All fixtures are function-scoped so every async fixture runs in the same
event loop as the test function (avoiding asyncio loop-mismatch errors).
Tables are created on first connection (CREATE TABLE IF NOT EXISTS) and
all rows are deleted after each test.
"""
import os
from unittest.mock import MagicMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.limiter import limiter
from app.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://jobscraper:jobscraper@localhost:5432/jobscraper_test",
)


# ─────────────────────────────────────────────────────────────────────────────
# Per-test engine — function-scoped so it shares the test's event loop
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    # Delete all rows between tests (faster than drop/recreate)
    async with eng.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    await eng.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# Setup session (for test data insertion only)
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def db(engine):
    """A session for inserting test data. Independent from client sessions."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# ─────────────────────────────────────────────────────────────────────────────
# ASGI test client — each request gets its own fresh session from the engine
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def client(engine):
    """Test client. Requests each get an independent session from the test engine."""
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Reset rate-limiter in-memory storage so limits from previous tests don't bleed in
    limiter._storage.reset()

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    # Patch Celery tasks at their definition site so lazy imports pick up the mock
    with patch("app.tasks.embed_tasks.embed_profile") as mock_ep, \
         patch("app.tasks.embed_tasks.compute_user_matches") as mock_cu, \
         patch("app.tasks.embed_tasks.embed_job") as mock_ej:
        mock_ep.delay = MagicMock(return_value=None)
        mock_cu.delay = MagicMock(return_value=None)
        mock_ej.delay = MagicMock(return_value=None)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def register_user(client: AsyncClient, email: str, password: str) -> str:
    """Register a user and return the access token."""
    resp = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    token = await register_user(client, email, password)
    return {"Authorization": f"Bearer {token}"}
