"""
Fetches job listings from company Greenhouse boards via their public API.
No authentication required. Returns standardized job dicts.

API: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

Board tokens are the slug that appears in https://boards.greenhouse.io/{token}
Run scripts/seed_greenhouse_companies.py to discover more tokens from the
Greenhouse directory.
"""
import logging
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# 200+ curated companies known to use Greenhouse.
# Tokens are the lowercase slugs used in their Greenhouse board URLs.
GREENHOUSE_COMPANIES: list[str] = [
    # ── AI / ML ──────────────────────────────────────────────────────────────
    "anthropic", "openai", "cohere", "scale", "weights-biases",
    "huggingface", "together-ai", "mistral", "perplexity", "imbue",
    "adept", "inflection", "stability", "runway", "jasper",
    "labelbox", "snorkel", "aquarium", "arize", "fiddler",
    # ── Data / Analytics ─────────────────────────────────────────────────────
    "databricks", "snowflake", "dbt-labs", "segment", "amplitude",
    "mixpanel", "heap", "fullstory", "contentsquare", "glean",
    "atlan", "alation", "collibra", "monte-carlo", "anomalo",
    "fivetran", "airbyte", "hightouch", "census", "polytomic",
    # ── Developer Tools / Infrastructure ────────────────────────────────────
    "hashicorp", "pagerduty", "datadog", "grafana", "newrelic",
    "elastic", "confluent", "astronomer", "prefect", "dagster",
    "sentry", "linear", "retool", "coda", "hex",
    "readme", "postman", "stoplight", "apiary", "launchdarkly",
    "split", "statsig", "eppo", "growthbook", "optimizely",
    # ── Communications / Productivity ────────────────────────────────────────
    "twilio", "sendgrid", "mailchimp", "klaviyo", "iterable",
    "braze", "attentive", "yotpo", "gorgias", "zendesk",
    "intercom", "front", "liveblocks", "daily", "agora",
    # ── Fintech / Payments ───────────────────────────────────────────────────
    "stripe", "brex", "ramp", "mercury", "moderntreasury",
    "plaid", "lithic", "unit", "column", "marqeta",
    "chime", "current", "dave", "albert", "brigit",
    "gusto", "rippling", "deel", "remote", "oyster",
    "carta", "pulley", "shareworks", "angelist",
    # ── E-commerce / Marketplace ─────────────────────────────────────────────
    "shopify", "faire", "pipe", "settle", "clearco",
    "recharge", "gorgias", "okendo", "loop-returns", "narvar",
    # ── Security / Identity ──────────────────────────────────────────────────
    "crowdstrike", "sentinelone", "lacework", "orca", "wiz",
    "snyk", "veracode", "checkmarx", "sonatype", "semgrep",
    "1password", "bitwarden", "keeper", "delinea", "beyondtrust",
    "okta", "auth0", "stytch", "descope", "workos",
    # ── HR / People ──────────────────────────────────────────────────────────
    "lattice", "leapsome", "culture-amp", "betterworks", "workboard",
    "hibob", "personio", "bamboohr", "namely", "paylocity",
    "hirequest", "greenhouse", "lever", "ashby",
    # ── Health / Bio ─────────────────────────────────────────────────────────
    "benchling", "veeva", "medidata", "flatiron", "tempus",
    "color", "hims-hers", "ro", "cerebral", "spring-health",
    "headway", "alma", "lyra", "brightline",
    # ── Legal / Compliance ───────────────────────────────────────────────────
    "clio", "litify", "filevine", "mycase", "smokeball",
    "truework", "hireright", "sterling", "checkr", "evident",
    # ── Real Estate / PropTech ───────────────────────────────────────────────
    "opendoor", "offerpad", "orchard", "homeward", "knock",
    "divvy", "roofstock", "fundrise", "cadre", "yieldstreet",
    # ── Logistics / Supply Chain ─────────────────────────────────────────────
    "flexport", "samsara", "project44", "fourkites", "stord",
    "shipbob", "shipmonk", "ware2go", "deliverr",
    # ── EdTech ───────────────────────────────────────────────────────────────
    "coursera", "duolingo", "chegg", "noodle", "outlier",
    "minerva", "lambda-school", "springboard", "careerfoundry",
    # ── General Tech (public & late-stage) ───────────────────────────────────
    "airbnb", "figma", "notion", "airtable", "miro",
    "asana", "clickup", "monday", "smartsheet",
    "hubspot", "salesforce", "zendesk", "freshworks",
    "gitlab", "grafana", "elastic",
    "coinbase", "kraken", "gemini", "paxos",
]

# Remove duplicates while preserving order
_seen: set[str] = set()
GREENHOUSE_COMPANIES = [t for t in GREENHOUSE_COMPANIES if not (_seen.add(t) or t in _seen)]  # type: ignore[func-returns-value]

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

        title = job.get("title", "")
        description = job.get("content", "")

        jobs.append({
            "source": "greenhouse",
            "external_id": str(job["id"]),
            "company": token,
            "title": title,
            "location": location,
            "is_remote": "remote" in location.lower() or "remote" in title.lower(),
            "description": description[:8000] if description else "",
            "url": job.get("absolute_url", ""),
        })
    return jobs


def fetch_all_greenhouse_jobs(
    companies: list[str] | None = None,
    delay: float = 0.3,
) -> list[dict]:
    """
    Fetch jobs from all (or a specified subset of) Greenhouse companies.

    Args:
        companies: Override the default company list (useful for targeted refreshes).
        delay: Seconds to sleep between requests. Keep >= 0.2 to be polite.
    """
    targets = companies or GREENHOUSE_COMPANIES
    all_jobs: list[dict] = []

    with httpx.Client(headers={"User-Agent": "JobMatcher/1.0 (personal research)"}) as client:
        for i, token in enumerate(targets):
            try:
                jobs = _fetch_company_jobs(client, token)
                all_jobs.extend(jobs)
                logger.debug("[Greenhouse] %s → %d jobs", token, len(jobs))
            except Exception as exc:
                logger.warning("[Greenhouse] Failed to fetch %s: %s", token, exc)

            # Sleep between requests; add a longer pause every 50 requests
            time.sleep(delay if i % 50 != 49 else delay * 5)

    logger.info("[Greenhouse] Total: %d jobs from %d companies", len(all_jobs), len(targets))
    return all_jobs
