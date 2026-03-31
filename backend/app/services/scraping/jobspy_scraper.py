"""
Uses python-jobspy to scrape jobs from Indeed and ZipRecruiter.
Rate-limited and proxy-aware.

NOTE: Scraping LinkedIn/Glassdoor violates their ToS. This module defaults to
Indeed + ZipRecruiter which have lower enforcement risk for personal/research use.
Set SCRAPER_INCLUDE_LINKEDIN=true in .env to opt in (requires a proxy).
"""
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Default search terms used when no user profiles are available
DEFAULT_SEARCH_TERMS = [
    "software engineer",
    "backend engineer",
    "frontend engineer",
    "full stack engineer",
    "data engineer",
    "machine learning engineer",
    "devops engineer",
    "platform engineer",
    "product manager",
    "data scientist",
    "data analyst",
]


def fetch_jobspy_jobs(
    search_term: str,
    location: str = "United States",
    results_wanted: int = 50,
    include_linkedin: bool = False,
    hours_old: int = 168,  # 7 days
) -> list[dict]:
    """
    Scrape jobs for a single search term via JobSpy.

    Args:
        search_term: Job title / keyword query.
        location: Geographic filter.
        results_wanted: Max results per site.
        include_linkedin: Opt-in to LinkedIn (requires proxy, violates ToS).
        hours_old: Only return jobs posted within this many hours.
    """
    try:
        from jobspy import scrape_jobs  # type: ignore
    except ImportError:
        logger.error("python-jobspy not installed. Run: pip install jobspy")
        return []

    sites = ["indeed", "zip_recruiter"]
    if include_linkedin and settings.scraper_proxy_url:
        sites.append("linkedin")

    proxy = settings.scraper_proxy_url

    try:
        df = scrape_jobs(
            site_name=sites,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            country_indeed="USA",
            proxies=[proxy] if proxy else None,
        )
    except Exception as exc:
        logger.error("[JobSpy] Scrape failed for '%s': %s", search_term, exc)
        return []

    jobs = []
    for _, row in df.iterrows():
        salary_min = salary_max = None
        try:
            if row.get("min_amount") and str(row["min_amount"]) not in ("nan", "None"):
                salary_min = int(float(row["min_amount"]))
            if row.get("max_amount") and str(row["max_amount"]) not in ("nan", "None"):
                salary_max = int(float(row["max_amount"]))
        except (ValueError, TypeError):
            pass

        job_url = str(row.get("job_url") or "")
        external_id = str(row.get("id") or job_url)

        jobs.append({
            "source": f"jobspy_{row.get('site', 'unknown')}",
            "external_id": external_id,
            "company": str(row.get("company") or ""),
            "title": str(row.get("title") or ""),
            "location": str(row.get("location") or ""),
            "is_remote": bool(row.get("is_remote", False)),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "description": str(row.get("description") or "")[:8000],
            "url": job_url,
        })

    logger.info("[JobSpy] '%s' @ %s → %d jobs", search_term, location, len(jobs))
    return jobs


async def collect_search_terms_from_profiles(db) -> list[str]:
    """
    Pull distinct desired_titles from all user profiles and normalise them
    into a deduplicated list of search terms to feed to JobSpy.
    Capped at 30 unique terms to avoid flooding the scrapers.
    """
    from sqlalchemy import func, select

    from app.models.profile import Profile

    result = await db.execute(
        select(func.unnest(Profile.desired_titles).label("title"))
        .distinct()
        .limit(100)
    )
    profile_titles = [row.title.strip().lower() for row in result.all() if row.title.strip()]

    # Merge with defaults; profile titles take precedence
    combined = list(dict.fromkeys(profile_titles + DEFAULT_SEARCH_TERMS))
    return combined[:30]
