"""
Thin wrapper around sentence-transformers.
Model is loaded once at process startup and reused.
"""
from functools import lru_cache
from typing import Union

from app.config import settings


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model)


def embed(text: Union[str, list[str]]) -> list:
    """
    Embed a single string or a list of strings.
    Returns a list of floats (single) or list of lists (batch).
    """
    model = get_model()
    result = model.encode(text, normalize_embeddings=True)
    if isinstance(text, str):
        return result.tolist()
    return [r.tolist() for r in result]


def embed_job(job) -> list[float]:
    """Combine title + company + description into a single embedding."""
    parts = [job.title, job.company]
    if job.description:
        # Truncate description to avoid blowing the context window
        parts.append(job.description[:2000])
    return embed(" | ".join(parts))


def embed_profile(profile) -> list[float]:
    """Combine resume text + desired titles + skills into a single embedding."""
    parts = []
    if profile.resume_text:
        parts.append(profile.resume_text[:3000])
    if profile.desired_titles:
        parts.append("Desired roles: " + ", ".join(profile.desired_titles))
    if profile.skills:
        parts.append("Skills: " + ", ".join(profile.skills))
    return embed(" | ".join(parts) if parts else "job seeker")
