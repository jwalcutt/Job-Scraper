"""Tests for GET /jobs/{id}/skills-gap endpoint and llm.skills_gap function.

Covers:
- Endpoint auth (401 without token)
- 404 when job or profile not found
- skills_gap() returns empty lists when no API key (graceful degradation)
- skills_gap() returns empty lists when profile has no skills and no resume
- skills_gap() uses resume_text when skills list is empty
- Endpoint returns 200 with the correct shape
"""
from unittest.mock import MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.profile import Profile
from app.services.llm import skills_gap
from tests.conftest import auth_headers, register_user

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _insert_job(db: AsyncSession, **kwargs) -> Job:
    defaults = dict(
        external_id="sg-job-1",
        source="greenhouse",
        company="Acme Corp",
        title="Backend Engineer",
        description="We need Python, FastAPI, PostgreSQL, Docker, and Kubernetes expertise.",
    )
    defaults.update(kwargs)
    job = Job(**defaults)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint auth tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSkillsGapAuth:
    async def test_unauthenticated_returns_401(self, client: AsyncClient, db: AsyncSession):
        job = await _insert_job(db, external_id="sg-auth-1")
        resp = await client.get(f"/jobs/{job.id}/skills-gap")
        assert resp.status_code == 401

    async def test_nonexistent_job_returns_404(self, client: AsyncClient):
        headers = await auth_headers(client, "sgauth1@example.com", "pass1234")
        resp = await client.get("/jobs/999999/skills-gap", headers=headers)
        assert resp.status_code == 404

    async def test_no_profile_returns_404(self, client: AsyncClient, db: AsyncSession):
        """User exists but profile row not yet created."""
        job = await _insert_job(db, external_id="sg-noprofile-1")
        # Register directly so no profile is created in this flow
        token = await register_user(client, "sgnoprofile@example.com", "pass1234")
        headers = {"Authorization": f"Bearer {token}"}

        # Delete any auto-created profile so we hit the 404 branch
        from sqlalchemy import delete, select

        from app.models.user import User
        user_result = await db.execute(select(User).where(User.email == "sgnoprofile@example.com"))
        user = user_result.scalar_one()
        await db.execute(delete(Profile).where(Profile.user_id == user.id))
        await db.commit()

        resp = await client.get(f"/jobs/{job.id}/skills-gap", headers=headers)
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# llm.skills_gap() unit tests (no API calls made)
# ─────────────────────────────────────────────────────────────────────────────

class TestSkillsGapFunction:
    def _make_profile(self, skills=None, resume_text=None):
        p = MagicMock()
        p.skills = skills or []
        p.resume_text = resume_text
        return p

    def _make_job(self, description="Requires Python, Docker, Kubernetes."):
        j = MagicMock()
        j.title = "Backend Engineer"
        j.company = "Acme"
        j.description = description
        j.id = 1
        return j

    def test_returns_no_api_key_error_when_key_missing(self):
        """No ANTHROPIC_API_KEY → error='no_api_key'."""
        with patch("app.services.llm.settings") as mock_settings:
            mock_settings.anthropic_api_key = None
            result = skills_gap(self._make_profile(skills=["Python"]), self._make_job())
        assert result["error"] == "no_api_key"
        assert result["matching"] == []
        assert result["missing"] == []

    def test_returns_no_profile_data_error_when_profile_empty(self):
        """Profile has neither skills nor resume — error='no_profile_data'."""
        with patch("app.services.llm.settings") as mock_settings:
            mock_settings.anthropic_api_key = "fake-key"
            result = skills_gap(self._make_profile(skills=[], resume_text=None), self._make_job())
        assert result["error"] == "no_profile_data"
        assert result["matching"] == []
        assert result["missing"] == []

    def test_returns_insufficient_credits_error_on_billing_failure(self):
        """API call that fails with 'credit balance too low' → error='insufficient_credits'."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception(
            "400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
            "'message': 'Your credit balance is too low to access the Anthropic API.'}}"
        )

        with patch("app.services.llm.settings") as mock_settings, \
             patch("app.services.llm._client", return_value=mock_client):
            mock_settings.anthropic_api_key = "fake-key"
            result = skills_gap(
                self._make_profile(skills=["Python"]),
                self._make_job(),
            )
        assert result["error"] == "insufficient_credits"
        assert result["matching"] == []
        assert result["missing"] == []

    def test_returns_api_error_on_generic_failure(self):
        """Generic API failure → error='api_error'."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Connection timeout")

        with patch("app.services.llm.settings") as mock_settings, \
             patch("app.services.llm._client", return_value=mock_client):
            mock_settings.anthropic_api_key = "fake-key"
            result = skills_gap(
                self._make_profile(skills=["Python"]),
                self._make_job(),
            )
        assert result["error"] == "api_error"

    def test_uses_resume_text_when_skills_empty(self):
        """When skills is empty but resume_text is present, Claude should be called."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"matching": ["Python"], "missing": ["Kubernetes"]}')]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        profile = self._make_profile(skills=[], resume_text="Experienced Python developer.")
        job = self._make_job()

        with patch("app.services.llm.settings") as mock_settings, \
             patch("app.services.llm._client", return_value=mock_client):
            mock_settings.anthropic_api_key = "fake-key"
            result = skills_gap(profile, job)

        assert result["matching"] == ["Python"]
        assert result["missing"] == ["Kubernetes"]
        # Confirm the call included resume text
        call_prompt = mock_client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Resume excerpt" in call_prompt

    def test_uses_skills_list_when_available(self):
        """When skills list is non-empty, it should be included in the prompt."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"matching": ["FastAPI"], "missing": ["Go"]}')]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        profile = self._make_profile(skills=["Python", "FastAPI"], resume_text=None)
        job = self._make_job()

        with patch("app.services.llm.settings") as mock_settings, \
             patch("app.services.llm._client", return_value=mock_client):
            mock_settings.anthropic_api_key = "fake-key"
            skills_gap(profile, job)

        call_prompt = mock_client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Python" in call_prompt
        assert "FastAPI" in call_prompt

    def test_handles_json_parse_error_gracefully(self):
        """Malformed JSON from Claude falls back to empty lists with api_error code."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Sorry, I cannot help with that.")]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("app.services.llm.settings") as mock_settings, \
             patch("app.services.llm._client", return_value=mock_client):
            mock_settings.anthropic_api_key = "fake-key"
            result = skills_gap(
                self._make_profile(skills=["Python"]),
                self._make_job(),
            )
        assert result["matching"] == []
        assert result["missing"] == []
        assert result["error"] in ("api_error", None)  # json parse error → api_error

    def test_strips_markdown_code_fences(self):
        """Claude sometimes wraps JSON in ```json ... ``` — this should be stripped."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text='```json\n{"matching": ["Python"], "missing": []}\n```'
        )]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("app.services.llm.settings") as mock_settings, \
             patch("app.services.llm._client", return_value=mock_client):
            mock_settings.anthropic_api_key = "fake-key"
            result = skills_gap(
                self._make_profile(skills=["Python"]),
                self._make_job(),
            )
        assert result["matching"] == ["Python"]
        assert result["missing"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint integration (no real API key — returns empty, verifies 200 shape)
# ─────────────────────────────────────────────────────────────────────────────

class TestSkillsGapEndpoint:
    async def test_returns_200_with_correct_shape(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Endpoint returns 200 with matching/missing lists (empty when no API key)."""
        job = await _insert_job(db, external_id="sg-endpoint-1")
        headers = await auth_headers(client, "sgendpoint@example.com", "pass1234")

        resp = await client.get(f"/jobs/{job.id}/skills-gap", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "matching" in body
        assert "missing" in body
        assert isinstance(body["matching"], list)
        assert isinstance(body["missing"], list)
