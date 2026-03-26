"""Tests for POST /auth/register and POST /auth/login."""
import pytest
from httpx import AsyncClient


class TestRegister:
    async def test_success(self, client: AsyncClient):
        resp = await client.post(
            "/auth/register", json={"email": "alice@example.com", "password": "secret123"}
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_duplicate_email(self, client: AsyncClient):
        payload = {"email": "bob@example.com", "password": "secret123"}
        await client.post("/auth/register", json=payload)
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    async def test_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            "/auth/register", json={"email": "not-an-email", "password": "secret123"}
        )
        assert resp.status_code == 422

    async def test_password_too_short_still_registers(self, client: AsyncClient):
        """Minimum password length is enforced at the route level (≥1 char from pydantic str)."""
        resp = await client.post(
            "/auth/register", json={"email": "charlie@example.com", "password": "x"}
        )
        # No minimum enforced at register — auth router accepts any non-empty string
        assert resp.status_code == 201


class TestLogin:
    async def test_success(self, client: AsyncClient):
        await client.post(
            "/auth/register", json={"email": "diana@example.com", "password": "hunter2"}
        )
        resp = await client.post(
            "/auth/login",
            data={"username": "diana@example.com", "password": "hunter2"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_wrong_password(self, client: AsyncClient):
        await client.post(
            "/auth/register", json={"email": "eve@example.com", "password": "correct"}
        )
        resp = await client.post(
            "/auth/login",
            data={"username": "eve@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_unknown_email(self, client: AsyncClient):
        resp = await client.post(
            "/auth/login",
            data={"username": "ghost@example.com", "password": "any"},
        )
        assert resp.status_code == 401

    async def test_missing_credentials(self, client: AsyncClient):
        resp = await client.post("/auth/login", data={})
        assert resp.status_code == 422
