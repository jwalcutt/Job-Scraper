"""
Fetches job listings from Lever-powered company career pages.
Lever exposes a public JSON endpoint per company (unofficial but stable).

URL: https://api.lever.co/v0/postings/{company}?mode=json
"""
import logging
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# 200+ companies known to use Lever.
# Slugs are the lowercase identifiers used in https://jobs.lever.co/{slug}
LEVER_COMPANIES: list[str] = [
    # ── Consumer / Social ────────────────────────────────────────────────────
    "netflix", "pinterest", "reddit", "discord", "snap",
    "tiktok", "bytedance", "quora", "medium", "substack",
    # ── Ride-share / Delivery ────────────────────────────────────────────────
    "lyft", "doordash", "instacart", "gopuff", "getaround",
    "turo", "sonder", "vacasa",
    # ── Design / Collaboration ───────────────────────────────────────────────
    "canva", "miro", "loom", "descript", "invision",
    "framer", "webflow", "wix", "squarespace",
    # ── Productivity / No-code ───────────────────────────────────────────────
    "clickup", "basecamp", "craft", "capacities",
    "roamresearch", "tana", "fibery", "heptabase",
    # ── Fintech ──────────────────────────────────────────────────────────────
    "robinhood", "wealthfront", "betterment", "acorns",
    "stash", "sofi", "chime", "varo", "greenlight",
    "affirm", "klarna", "afterpay", "sezzle",
    "nerdwallet", "creditkarma", "experian",
    "adyen", "checkout", "paytm", "razorpay",
    # ── Security ─────────────────────────────────────────────────────────────
    "cloudflare", "fastly", "akamai",
    "qualys", "tenable", "rapid7", "vulcan",
    "abnormalsecurity", "proofpoint", "mimecast",
    "huntress", "blumira", "expel", "armorblox",
    # ── Developer Tools ──────────────────────────────────────────────────────
    "hashicorp", "netlify", "supabase", "planetscale",
    "fly", "railway", "render", "northflank",
    "vercel", "deno", "bun",
    "algolia", "meilisearch", "typesense",
    "contentful", "sanity", "ghost", "prismic",
    "auth0", "stytch", "clerk", "descope",
    "posthog", "june", "hyperping", "betterstack",
    "doppler", "infisical", "akeyless",
    "temporal", "inngest", "trigger",
    "neon", "turso", "xata", "convex",
    "prisma", "drizzle", "hasura", "graphcms",
    # ── Data / Analytics ─────────────────────────────────────────────────────
    "dune", "mode", "metabase", "redash", "preset",
    "lightdash", "cube", "transform", "omni",
    "starburst", "ahana", "imply",
    # ── HR / Recruiting ──────────────────────────────────────────────────────
    "lever", "ashby", "workable", "recruitee", "teamtailor",
    "breezyhr", "jazzhr", "pinpointhq",
    "hirequest", "toptal", "andela", "turing",
    # ── EdTech ───────────────────────────────────────────────────────────────
    "kahoot", "quizlet", "brainly", "varsitytutors",
    "outschool", "synthesis", "thinkthroughmath",
    "codecademy", "treehouse", "pluralsight",
    # ── Health / Wellness ────────────────────────────────────────────────────
    "calm", "headspace", "noom", "ww",
    "teladoc", "mdlive", "amwell", "doctorondemand",
    "omadahealth", "livongo", "virta",
    "cityblock", "oscar", "clover",
    # ── Climate / Energy ─────────────────────────────────────────────────────
    "climateai", "pachama", "terraformation", "planvivo",
    "arcadia", "octopusenergy", "tesla", "rivian",
    "proterra", "xos", "canoo", "fisker",
    "form-energy", "eos-energy", "ambri",
    # ── Real Estate ──────────────────────────────────────────────────────────
    "compass", "redfin", "realtor", "homesnap",
    "matterport", "vrbo", "sonder",
    # ── Logistics ────────────────────────────────────────────────────────────
    "convoy", "transfix", "loadsmart", "mastery-logistics",
    "shipwell", "turvo", "project44",
    # ── General / Late-stage ─────────────────────────────────────────────────
    "shopify", "hubspot", "zendesk", "intercom",
    "monday", "asana", "notion", "airtable",
    "figma", "miro", "loom",
    "twilio", "sendgrid", "mailchimp",
    "datadog", "pagerduty", "splunk",
    "crowdstrike", "okta", "ping",
    "gitlab", "github", "atlassian",
    "elastic", "confluent", "cloudera",
]

# Deduplicate while preserving order
LEVER_COMPANIES = list(dict.fromkeys(LEVER_COMPANIES))

BASE_URL = "https://api.lever.co/v0/postings/{company}"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_company_jobs(client: httpx.Client, company: str) -> list[dict]:
    resp = client.get(
        BASE_URL.format(company=company),
        params={"mode": "json"},
        timeout=15,
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()

    postings = resp.json()
    jobs = []
    for p in postings:
        categories = p.get("categories", {})
        # Lever stores location in categories.location or categories.allLocations
        all_locations = categories.get("allLocations") or []
        location = categories.get("location") or (all_locations[0] if all_locations else "")
        commitment = categories.get("commitment", "")

        is_remote = (
            "remote" in location.lower()
            or "remote" in commitment.lower()
            or "distributed" in location.lower()
        )

        # Prefer plain text description over HTML
        description = p.get("descriptionPlain") or p.get("description") or ""
        # Also append the lists sections (requirements, etc.)
        for lst in p.get("lists", []):
            description += f"\n\n{lst.get('text', '')}: {lst.get('content', '')}"

        jobs.append({
            "source": "lever",
            "external_id": p.get("id", ""),
            "company": company,
            "title": p.get("text", ""),
            "location": location,
            "is_remote": is_remote,
            "description": description[:8000],
            "url": p.get("hostedUrl", ""),
        })
    return jobs


def fetch_all_lever_jobs(
    companies: list[str] | None = None,
    delay: float = 0.3,
) -> list[dict]:
    """
    Fetch jobs from all (or a subset of) Lever companies.

    Args:
        companies: Override default list (e.g. for targeted refresh).
        delay: Seconds between requests.
    """
    targets = companies or LEVER_COMPANIES
    all_jobs: list[dict] = []

    with httpx.Client(headers={"User-Agent": "JobMatcher/1.0 (personal research)"}) as client:
        for i, company in enumerate(targets):
            try:
                jobs = _fetch_company_jobs(client, company)
                all_jobs.extend(jobs)
                logger.debug("[Lever] %s → %d jobs", company, len(jobs))
            except Exception as exc:
                logger.warning("[Lever] Failed to fetch %s: %s", company, exc)

            time.sleep(delay if i % 50 != 49 else delay * 5)

    logger.info("[Lever] Total: %d jobs from %d companies", len(all_jobs), len(targets))
    return all_jobs
