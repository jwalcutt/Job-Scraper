"""
Fetches job listings from company Greenhouse boards via their public API.
No authentication required. Returns standardized job dicts.

API: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# Curated list of popular companies using Greenhouse
# Expand this list over time; see scripts/seed_greenhouse_companies.py for bulk import
GREENHOUSE_COMPANIES = [
    "airbnb", "stripe", "coinbase", "figma", "notion", "airtable",
    "brex", "chime", "plaid", "rippling", "gusto", "lattice",
    "scale", "weights-biases", "huggingface", "anthropic", "openai",
    "databricks", "snowflake", "dbt-labs", "segment", "twilio",
    "zendesk", "intercom", "amplitude", "mixpanel", "linear",
]

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_company_jobs(client: httpx.Client, token: str) -> list[dict]:
    resp = client.get(BASE_URL.format(token=token), params={"content": "true"}, timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    jobs = []
    for job in data.get("jobs", []):
        location = ""
        if job.get("offices"):
            location = job["offices"][0].get("name", "")
        elif job.get("location"):
            location = job["location"].get("name", "")

        jobs.append({
            "source": "greenhouse",
            "external_id": str(job["id"]),
            "company": token,
            "title": job.get("title", ""),
            "location": location,
            "is_remote": "remote" in location.lower() or "remote" in job.get("title", "").lower(),
            "description": job.get("content", ""),
            "url": job.get("absolute_url", ""),
        })
    return jobs


def fetch_all_greenhouse_jobs() -> list[dict]:
    all_jobs: list[dict] = []
    with httpx.Client(headers={"User-Agent": "JobMatcher/1.0 (personal research)"}) as client:
        for token in GREENHOUSE_COMPANIES:
            try:
                jobs = _fetch_company_jobs(client, token)
                all_jobs.extend(jobs)
                time.sleep(0.5)  # Be polite
            except Exception as e:
                print(f"[Greenhouse] Failed to fetch {token}: {e}")
    return all_jobs
