"""Tests for GET /profile and PATCH /profile."""
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestGetProfile:
    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/profile")
        assert resp.status_code == 401

    async def test_empty_profile_after_register(self, client: AsyncClient):
        headers = await auth_headers(client, "frank@example.com", "pass1234")
        resp = await client.get("/profile", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        # Freshly-registered user has no titles, skills, and has_resume is False
        assert body["desired_titles"] == []
        assert body["skills"] == []
        assert body["has_resume"] is False


class TestPatchProfile:
    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.patch("/profile", json={"full_name": "Test"})
        assert resp.status_code == 401

    async def test_update_full_name(self, client: AsyncClient):
        headers = await auth_headers(client, "grace@example.com", "pass1234")
        resp = await client.patch("/profile", json={"full_name": "Grace Hopper"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Grace Hopper"

    async def test_update_desired_titles(self, client: AsyncClient):
        headers = await auth_headers(client, "heidi@example.com", "pass1234")
        resp = await client.patch(
            "/profile",
            json={"desired_titles": ["Software Engineer", "Backend Developer"]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "Software Engineer" in resp.json()["desired_titles"]

    async def test_update_remote_preference(self, client: AsyncClient):
        headers = await auth_headers(client, "ivan@example.com", "pass1234")
        for pref in ("REMOTE", "HYBRID", "ONSITE", "ANY"):
            resp = await client.patch(
                "/profile", json={"remote_preference": pref}, headers=headers
            )
            assert resp.status_code == 200
            assert resp.json()["remote_preference"] == pref

    async def test_update_salary(self, client: AsyncClient):
        headers = await auth_headers(client, "judy@example.com", "pass1234")
        resp = await client.patch(
            "/profile", json={"desired_salary_min": 100000, "desired_salary_max": 150000},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["desired_salary_min"] == 100000
        assert body["desired_salary_max"] == 150000

    async def test_partial_update_preserves_other_fields(self, client: AsyncClient):
        headers = await auth_headers(client, "karl@example.com", "pass1234")
        await client.patch("/profile", json={"full_name": "Karl"}, headers=headers)
        await client.patch("/profile", json={"location": "Berlin"}, headers=headers)
        resp = await client.get("/profile", headers=headers)
        body = resp.json()
        assert body["full_name"] == "Karl"
        assert body["location"] == "Berlin"
