"""Tests for /applications/* endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from tests.conftest import auth_headers


async def _insert_job(db: AsyncSession, external_id: str = "app-job-1") -> Job:
    job = Job(
        external_id=external_id,
        source="greenhouse",
        company="Beta Inc",
        title="Backend Engineer",
        location="Remote",
        is_remote=True,
        description="Build the backend.",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


class TestCreateApplication:
    async def test_unauthenticated(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db)
        resp = await client.post(f"/applications/{job.id}")
        assert resp.status_code == 401

    async def test_success(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, "new-1")
        headers = await auth_headers(client, "tina@example.com", "pass1234")
        resp = await client.post(f"/applications/{job.id}", headers=headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["job_id"] == job.id
        assert body["status"] == "applied"

    async def test_idempotent(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, "idem-app-1")
        headers = await auth_headers(client, "uma@example.com", "pass1234")
        await client.post(f"/applications/{job.id}", headers=headers)
        resp = await client.post(f"/applications/{job.id}", headers=headers)
        assert resp.status_code in (200, 201)

        resp = await client.get("/applications", headers=headers)
        assert len(resp.json()) == 1  # no duplicate

    async def test_nonexistent_job(self, client: AsyncClient):
        headers = await auth_headers(client, "vera@example.com", "pass1234")
        resp = await client.post("/applications/999999", headers=headers)
        assert resp.status_code == 404


class TestListApplications:
    async def test_empty_list(self, client: AsyncClient):
        headers = await auth_headers(client, "will@example.com", "pass1234")
        resp = await client.get("/applications", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_created_applications(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, "list-app-1")
        headers = await auth_headers(client, "xena@example.com", "pass1234")
        await client.post(f"/applications/{job.id}", headers=headers)

        resp = await client.get("/applications", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["job_title"] == "Backend Engineer"


class TestUpdateApplication:
    async def test_update_status(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, "upd-app-1")
        headers = await auth_headers(client, "yara@example.com", "pass1234")
        create_resp = await client.post(f"/applications/{job.id}", headers=headers)
        app_id = create_resp.json()["id"]

        for status in ("phone_screen", "interview", "offer", "rejected"):
            resp = await client.patch(
                f"/applications/{app_id}", json={"status": status}, headers=headers
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == status

    async def test_update_notes(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, "notes-app-1")
        headers = await auth_headers(client, "zack@example.com", "pass1234")
        create_resp = await client.post(f"/applications/{job.id}", headers=headers)
        app_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/applications/{app_id}", json={"notes": "Great company culture"}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Great company culture"

    async def test_cannot_update_other_users_application(
        self, client: AsyncClient, db: AsyncSession
    ):
        job = await _insert_job(db, "other-app-1")
        headers_a = await auth_headers(client, "alice2@example.com", "pass1234")
        headers_b = await auth_headers(client, "bob2@example.com", "pass1234")

        create_resp = await client.post(f"/applications/{job.id}", headers=headers_a)
        app_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/applications/{app_id}", json={"status": "rejected"}, headers=headers_b
        )
        assert resp.status_code == 404


class TestDeleteApplication:
    async def test_delete(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, "del-app-1")
        headers = await auth_headers(client, "carol2@example.com", "pass1234")
        create_resp = await client.post(f"/applications/{job.id}", headers=headers)
        app_id = create_resp.json()["id"]

        resp = await client.delete(f"/applications/{app_id}", headers=headers)
        assert resp.status_code in (200, 204)

        resp = await client.get("/applications", headers=headers)
        assert resp.json() == []

    async def test_delete_nonexistent(self, client: AsyncClient):
        headers = await auth_headers(client, "dave2@example.com", "pass1234")
        resp = await client.delete("/applications/999999", headers=headers)
        assert resp.status_code == 404
