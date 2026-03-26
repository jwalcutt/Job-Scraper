"""
Uses python-jobspy to scrape jobs from Indeed, ZipRecruiter, and (optionally)
LinkedIn. Rate-limited and proxy-aware.

NOTE: Scraping LinkedIn/Glassdoor violates their ToS. This module defaults to
Indeed + ZipRecruiter which have lower enforcement risk for personal/research use.
Set SCRAPER_INCLUDE_LINKEDIN=true in .env to enable LinkedIn (use a proxy).
"""
import os
from datetime import date

from app.config import settings


def fetch_jobspy_jobs(
    search_term: str,
    location: str = "United States",
    results_wanted: int = 50,
    include_linkedin: bool = False,
) -> list[dict]:
    from jobspy import scrape_jobs  # type: ignore

    sites = ["indeed", "zip_recruiter"]
    if include_linkedin and settings.scraper_proxy_url:
        sites.append("linkedin")

    proxy = settings.scraper_proxy_url

    df = scrape_jobs(
        site_name=sites,
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=24 * 7,  # last 7 days
        country_indeed="USA",
        proxies=[proxy] if proxy else None,
    )

    jobs = []
    for _, row in df.iterrows():
        salary_min = salary_max = None
        if row.get("min_amount") and not isinstance(row["min_amount"], float):
            salary_min = int(row["min_amount"])
        if row.get("max_amount") and not isinstance(row["max_amount"], float):
            salary_max = int(row["max_amount"])

        jobs.append({
            "source": f"jobspy_{row.get('site', 'unknown')}",
            "external_id": str(row.get("id", row.get("job_url", ""))),
            "company": str(row.get("company", "")),
            "title": str(row.get("title", "")),
            "location": str(row.get("location", "")),
            "is_remote": bool(row.get("is_remote", False)),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "description": str(row.get("description", ""))[:5000],
            "url": str(row.get("job_url", "")),
        })

    return jobs
