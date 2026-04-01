"""
Claude API wrappers for LLM-powered features:
  - match_explanation: one-sentence why a job fits a user
  - rerank_and_explain: re-rank top-N matches by actual fit
  - skills_gap: compare user skills to a job's requirements

All functions return None gracefully when ANTHROPIC_API_KEY is not set,
so the app works without LLM features in dev.
"""
import json
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_DESC = 800   # chars of job description sent to Claude
MAX_RESUME = 600 # chars of resume sent to Claude


def _client():
    if not settings.anthropic_api_key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _profile_summary(profile) -> str:
    parts = []
    if profile.desired_titles:
        parts.append(f"Desired roles: {', '.join(profile.desired_titles)}")
    if profile.skills:
        parts.append(f"Skills: {', '.join(profile.skills)}")
    if profile.years_experience:
        parts.append(f"Years of experience: {profile.years_experience}")
    if profile.remote_preference and profile.remote_preference != "ANY":
        parts.append(f"Work preference: {profile.remote_preference}")
    if profile.resume_text:
        parts.append(f"Resume excerpt: {profile.resume_text[:MAX_RESUME]}")
    return "\n".join(parts) if parts else "No profile details provided."


def match_explanation(profile, job) -> Optional[str]:
    """
    Return a single sentence (≤20 words) explaining why this job fits the user.
    Returns None if no API key is configured or on any error.
    """
    client = _client()
    if not client:
        return None

    desc = (job.description or "")[:MAX_DESC]
    prompt = (
        f"Job seeker profile:\n{_profile_summary(profile)}\n\n"
        f"Job: {job.title} at {job.company}\n"
        f"Description excerpt: {desc}\n\n"
        "In exactly one sentence (max 20 words), explain why this job is a strong match "
        "for this candidate. Be specific — mention a skill or experience. "
        "Do not start with 'This job' or 'The candidate'."
    )

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("[llm.match_explanation] job_id=%s: %s", job.id, exc)
        return None


def rerank_and_explain(profile, jobs_with_scores: list[tuple]) -> list[dict]:
    """
    Re-rank a list of (job, score) tuples by actual fit and generate explanations.

    Args:
        profile: Profile ORM object
        jobs_with_scores: list of (Job, float) — typically top-20 from vector search

    Returns:
        list of dicts: [{job_id, rank, score, explanation}, ...]
        Preserves original vector scores; only rank and explanation change.
        Falls back to original order if no API key or on error.
    """
    client = _client()
    if not client or not jobs_with_scores:
        return [
            {"job_id": job.id, "rank": i + 1, "score": score, "explanation": None}
            for i, (job, score) in enumerate(jobs_with_scores)
        ]

    job_list = "\n".join(
        f"{i+1}. [id={job.id}] {job.title} at {job.company} "
        f"(location: {job.location or 'unknown'}) — "
        f"{(job.description or '')[:200]}"
        for i, (job, _) in enumerate(jobs_with_scores)
    )

    prompt = (
        f"Job seeker profile:\n{_profile_summary(profile)}\n\n"
        f"Below are {len(jobs_with_scores)} job matches ordered by semantic similarity. "
        "Re-rank them by actual fit for this specific candidate (considering their skills, "
        "experience level, role preferences, and location). Provide a one-sentence explanation "
        "for each.\n\n"
        f"{job_list}\n\n"
        "Return ONLY a JSON array, no other text:\n"
        '[{"job_id": <int>, "rank": <int>, "explanation": "<one sentence>"}, ...]'
    )

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed: list[dict] = json.loads(raw)

        # Build a lookup from the original list
        score_by_id = {job.id: score for job, score in jobs_with_scores}
        result = []
        for item in parsed:
            jid = item.get("job_id")
            if jid in score_by_id:
                result.append({
                    "job_id": jid,
                    "rank": item.get("rank", 999),
                    "score": score_by_id[jid],
                    "explanation": item.get("explanation"),
                })
        return sorted(result, key=lambda x: x["rank"])

    except Exception as exc:
        logger.warning("[llm.rerank_and_explain] user_id=%s: %s", profile.user_id, exc)
        return [
            {"job_id": job.id, "rank": i + 1, "score": score, "explanation": None}
            for i, (job, score) in enumerate(jobs_with_scores)
        ]


def skills_gap(profile, job) -> dict:
    """
    Compare user skills against a job description.

    Returns:
        {"matching": ["Python", ...], "missing": ["Kubernetes", ...]}
        Returns empty lists if no API key or on error.
    """
    client = _client()
    if not client:
        return {"matching": [], "missing": [], "error": "no_api_key"}

    # Build candidate background: prefer explicit skills list; fall back to resume text
    if profile.skills:
        candidate_info = f"Skills: {', '.join(profile.skills)}"
        if profile.resume_text:
            candidate_info += f"\nResume excerpt: {profile.resume_text[:MAX_RESUME]}"
    elif profile.resume_text:
        candidate_info = f"Resume excerpt: {profile.resume_text[:MAX_RESUME]}"
    else:
        return {"matching": [], "missing": [], "error": "no_profile_data"}

    desc = (job.description or "")[:1200]

    prompt = (
        f"Job: {job.title} at {job.company}\n"
        f"Job description excerpt:\n{desc}\n\n"
        f"Candidate background:\n{candidate_info}\n\n"
        "Analyze the job requirements and identify:\n"
        "1. Skills the candidate HAS that are relevant to this job\n"
        "2. Skills the candidate is MISSING that are required or strongly preferred\n\n"
        "Return ONLY JSON, no other text:\n"
        '{"matching": ["skill1", "skill2"], "missing": ["skill3", "skill4"]}'
    )

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        result.setdefault("error", None)
        return result
    except Exception as exc:
        logger.warning("[llm.skills_gap] job_id=%s: %s", job.id, exc)
        err_str = str(exc)
        if "credit" in err_str.lower() or "balance" in err_str.lower() or "billing" in err_str.lower():
            error_code = "insufficient_credits"
        else:
            error_code = "api_error"
        return {"matching": [], "missing": [], "error": error_code}
