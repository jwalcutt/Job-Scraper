"""
Fetches job listings from Lever-powered company career pages.
Lever exposes a public (unofficial) JSON endpoint per company.

URL: https://api.lever.co/v0/postings/{company}?mode=json
"""
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

LEVER_COMPANIES = [
    "netflix", "uber", "lyft", "pinterest", "reddit", "discord",
    "canva", "miro", "loom", "asana", "monday", "clickup",
    "carta", "robinhood", "wealthfront", "stytch", "auth0",
    "hashicorp", "vercel", "netlify", "cloudflare", "fastly",
    "contentful", "sanity", "ghost", "supabase", "planetscale",
]

BASE_URL = "https://api.lever.co/v0/postings/{company}"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_company_jobs(client: httpx.Client, company: str) -> list[dict]:
    resp = client.get(BASE_URL.format(company=company), params={"mode": "json"}, timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    postings = resp.json()
    jobs = []
    for p in postings:
        categories = p.get("categories", {})
        location = categories.get("location", "") or categories.get("allLocations", [""])[0]
        commitment = categories.get("commitment", "")
        is_remote = "remote" in location.lower() or "remote" in commitment.lower()

        jobs.append({
            "source": "lever",
            "external_id": p.get("id", ""),
            "company": company,
            "title": p.get("text", ""),
            "location": location,
            "is_remote": is_remote,
            "description": p.get("descriptionPlain", "") or p.get("description", ""),
            "url": p.get("hostedUrl", ""),
        })
    return jobs


def fetch_all_lever_jobs() -> list[dict]:
    all_jobs: list[dict] = []
    with httpx.Client(headers={"User-Agent": "JobMatcher/1.0 (personal research)"}) as client:
        for company in LEVER_COMPANIES:
            try:
                jobs = _fetch_company_jobs(client, company)
                all_jobs.extend(jobs)
                time.sleep(0.5)
            except Exception as e:
                print(f"[Lever] Failed to fetch {company}: {e}")
    return all_jobs
