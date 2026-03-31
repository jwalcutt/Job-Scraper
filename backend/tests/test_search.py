"""Tests for GET /jobs/search endpoint (Bug 1 regression coverage).

Ensures:
- The endpoint returns 401 for unauthenticated requests (not a redirect).
- Authenticated users can search and receive results.
- Filters (remote, source) narrow results correctly.
- Short queries (< 2 chars) are rejected with 422.
- An empty result set is returned when no jobs match, not an error.
"""
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from tests.conftest import auth_headers


async def _insert_job(db: AsyncSession, **kwargs) -> Job:
    defaults = dict(
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


class TestSearchUnauthenticated:
    """Unauthenticated requests must return 401, not trigger a redirect."""

    async def test_returns_401_without_token(self, client: AsyncClient):
        resp = await client.get("/jobs/search?q=engineer")
        assert resp.status_code == 401

    async def test_returns_401_with_bad_token(self, client: AsyncClient):
        resp = await client.get(
            "/jobs/search?q=engineer",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401


class TestSearchAuthenticated:
    """Authenticated users get 200 responses with appropriate results."""

    async def test_empty_results_when_no_jobs(self, client: AsyncClient):
        headers = await auth_headers(client, "search1@example.com", "pass1234")
        resp = await client.get("/jobs/search?q=engineer", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_finds_matching_job_by_title(
        self, client: AsyncClient, db: AsyncSession
    ):
        await _insert_job(
            db,
            external_id="search-title-1",
            title="Backend Python Engineer",
            description="We build data pipelines.",
        )
        headers = await auth_headers(client, "search2@example.com", "pass1234")
        resp = await client.get("/jobs/search?q=python+engineer", headers=headers)
        assert resp.status_code == 200
        titles = [j["title"] for j in resp.json()]
        assert "Backend Python Engineer" in titles

    async def test_finds_matching_job_by_description(
        self, client: AsyncClient, db: AsyncSession
    ):
        await _insert_job(
            db,
            external_id="search-desc-1",
            title="Data Scientist",
            description="Experience with machine learning and PyTorch required.",
        )
        headers = await auth_headers(client, "search3@example.com", "pass1234")
        resp = await client.get("/jobs/search?q=machine+learning", headers=headers)
        assert resp.status_code == 200
        titles = [j["title"] for j in resp.json()]
        assert "Data Scientist" in titles

    async def test_no_match_returns_empty_list_not_error(
        self, client: AsyncClient, db: AsyncSession
    ):
        await _insert_job(
            db,
            external_id="search-nomatch-1",
            title="Accountant",
            description="Spreadsheets and financial reporting.",
        )
        headers = await auth_headers(client, "search4@example.com", "pass1234")
        resp = await client.get("/jobs/search?q=robotics", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_response_shape(self, client: AsyncClient, db: AsyncSession):
        await _insert_job(
            db,
            external_id="search-shape-1",
            title="Frontend Developer",
            description="React, TypeScript, Tailwind CSS.",
            url="https://example.com/job/1",
        )
        headers = await auth_headers(client, "search5@example.com", "pass1234")
        resp = await client.get("/jobs/search?q=react", headers=headers)
        assert resp.status_code == 200
        jobs = resp.json()
        assert len(jobs) >= 1
        job = jobs[0]
        for field in ("id", "title", "company", "location", "is_remote", "source", "url"):
            assert field in job, f"Missing field: {field}"


class TestSearchFilters:
    """Filter parameters correctly narrow search results."""

    async def test_remote_filter_true(self, client: AsyncClient, db: AsyncSession):
        await _insert_job(
            db,
            external_id="filter-remote-1",
            title="Remote DevOps Engineer",
            description="Cloud infrastructure management.",
            is_remote=True,
        )
        await _insert_job(
            db,
            external_id="filter-onsite-1",
            title="Onsite DevOps Engineer",
            description="Cloud infrastructure management.",
            is_remote=False,
        )
        headers = await auth_headers(client, "search6@example.com", "pass1234")
        resp = await client.get(
            "/jobs/search?q=devops+engineer&remote=true", headers=headers
        )
        assert resp.status_code == 200
        jobs = resp.json()
        assert all(j["is_remote"] for j in jobs)
        assert any(j["title"] == "Remote DevOps Engineer" for j in jobs)

    async def test_remote_filter_false(self, client: AsyncClient, db: AsyncSession):
        await _insert_job(
            db,
            external_id="filter-remote-2",
            title="Remote SRE Engineer",
            description="Site reliability engineering.",
            is_remote=True,
        )
        await _insert_job(
            db,
            external_id="filter-onsite-2",
            title="Onsite SRE Engineer",
            description="Site reliability engineering.",
            is_remote=False,
        )
        headers = await auth_headers(client, "search7@example.com", "pass1234")
        resp = await client.get(
            "/jobs/search?q=sre+engineer&remote=false", headers=headers
        )
        assert resp.status_code == 200
        jobs = resp.json()
        assert all(not j["is_remote"] for j in jobs)

    async def test_source_filter(self, client: AsyncClient, db: AsyncSession):
        await _insert_job(
            db,
            external_id="filter-src-1",
            source="lever",
            title="Lever Product Manager",
            description="Product strategy and roadmap ownership.",
        )
        await _insert_job(
            db,
            external_id="filter-src-2",
            source="greenhouse",
            title="Greenhouse Product Manager",
            description="Product strategy and roadmap ownership.",
        )
        headers = await auth_headers(client, "search8@example.com", "pass1234")
        resp = await client.get(
            "/jobs/search?q=product+manager&source=lever", headers=headers
        )
        assert resp.status_code == 200
        jobs = resp.json()
        assert all(j["source"] == "lever" for j in jobs)


class TestSearchValidation:
    """Query validation rejects bad inputs."""

    async def test_query_too_short_returns_422(self, client: AsyncClient):
        headers = await auth_headers(client, "search9@example.com", "pass1234")
        resp = await client.get("/jobs/search?q=a", headers=headers)
        assert resp.status_code == 422

    async def test_missing_query_returns_422(self, client: AsyncClient):
        headers = await auth_headers(client, "search10@example.com", "pass1234")
        resp = await client.get("/jobs/search", headers=headers)
        assert resp.status_code == 422

    async def test_limit_parameter_respected(
        self, client: AsyncClient, db: AsyncSession
    ):
        for i in range(5):
            await _insert_job(
                db,
                external_id=f"limit-test-{i}",
                title=f"Engineer Role {i}",
                description="Python backend development role.",
            )
        headers = await auth_headers(client, "search11@example.com", "pass1234")
        resp = await client.get("/jobs/search?q=engineer&limit=2", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 2
