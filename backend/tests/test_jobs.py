"""Tests for /jobs/* endpoints."""
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from tests.conftest import auth_headers


async def _insert_job(db: AsyncSession, **kwargs) -> Job:
    defaults = dict(
        external_id="ext-1",
        source="greenhouse",
        company="Acme Corp",
        title="Software Engineer",
        location="New York",
        is_remote=False,
        description="Build cool things with Python and React.",
    )
    defaults.update(kwargs)
    job = Job(**defaults)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


class TestMatchesStatus:
    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/jobs/matches/status")
        assert resp.status_code == 401

    async def test_fresh_user_status(self, client: AsyncClient):
        headers = await auth_headers(client, "lena@example.com", "pass1234")
        resp = await client.get("/jobs/matches/status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_embedding"] is False
        assert body["match_count"] == 0
        assert body["profile_complete"] is False


class TestGetMatches:
    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/jobs/matches")
        assert resp.status_code == 401

    async def test_returns_empty_list_for_new_user(self, client: AsyncClient):
        headers = await auth_headers(client, "mike@example.com", "pass1234")
        resp = await client.get("/jobs/matches", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_filter_params_accepted(self, client: AsyncClient):
        headers = await auth_headers(client, "nancy@example.com", "pass1234")
        resp = await client.get(
            "/jobs/matches?min_score=0.5&remote=true&title=engineer",
            headers=headers,
        )
        assert resp.status_code == 200


class TestSaveUnsaveJob:
    async def test_save_and_retrieve(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, external_id="save-1")
        headers = await auth_headers(client, "olivia@example.com", "pass1234")

        # Save
        resp = await client.post(f"/jobs/{job.id}/save", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["saved"] is True

        # Retrieve saved list
        resp = await client.get("/jobs/saved", headers=headers)
        assert resp.status_code == 200
        ids = [j["id"] for j in resp.json()]
        assert job.id in ids

    async def test_unsave(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, external_id="unsave-1")
        headers = await auth_headers(client, "peter@example.com", "pass1234")

        await client.post(f"/jobs/{job.id}/save", headers=headers)
        resp = await client.delete(f"/jobs/{job.id}/save", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["saved"] is False

        resp = await client.get("/jobs/saved", headers=headers)
        assert resp.json() == []

    async def test_save_idempotent(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, external_id="idem-1")
        headers = await auth_headers(client, "quinn@example.com", "pass1234")

        await client.post(f"/jobs/{job.id}/save", headers=headers)
        resp = await client.post(f"/jobs/{job.id}/save", headers=headers)
        assert resp.status_code == 200  # no duplicate error

        resp = await client.get("/jobs/saved", headers=headers)
        assert len(resp.json()) == 1


class TestGetJob:
    async def test_get_existing_job(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, external_id="detail-1")
        headers = await auth_headers(client, "rachel@example.com", "pass1234")
        resp = await client.get(f"/jobs/{job.id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Software Engineer"
        assert body["company"] == "Acme Corp"

    async def test_get_nonexistent_job(self, client: AsyncClient):
        headers = await auth_headers(client, "sam@example.com", "pass1234")
        resp = await client.get("/jobs/999999", headers=headers)
        assert resp.status_code == 404
