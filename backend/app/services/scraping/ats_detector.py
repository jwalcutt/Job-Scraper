"""
ATS type detector.

Given a careers page URL (or fetched HTML), returns the ATS platform name so
the right scraper can be dispatched.

Detection order (fast → slow):
  1. URL pattern matching (no network request needed)
  2. HTML fingerprinting via httpx (lightweight GET, no JS rendering)
"""
import re
from typing import Optional

import httpx

# ─────────────────────────────────────────────────────────────────────────────
# URL-based patterns (checked first — zero network cost)
# ─────────────────────────────────────────────────────────────────────────────

_URL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"myworkdayjobs\.com", re.I), "workday"),
    (re.compile(r"icims\.com", re.I), "icims"),
    (re.compile(r"greenhouse\.io|boards\.greenhouse\.io", re.I), "greenhouse"),
    (re.compile(r"lever\.co", re.I), "lever"),
    (re.compile(r"taleo\.net", re.I), "taleo"),
    (re.compile(r"successfactors\.(com|eu)", re.I), "successfactors"),
    (re.compile(r"smartrecruiters\.com", re.I), "smartrecruiters"),
    (re.compile(r"jobvite\.com", re.I), "jobvite"),
    (re.compile(r"ashbyhq\.com", re.I), "ashby"),
    (re.compile(r"rippling\.com.*jobs|jobs\.rippling\.com", re.I), "rippling"),
]

# ─────────────────────────────────────────────────────────────────────────────
# HTML fingerprints (checked on fetched page source)
# ─────────────────────────────────────────────────────────────────────────────

_HTML_FINGERPRINTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"myworkdayjobs\.com|wd\d+\.myworkdayjobs", re.I), "workday"),
    (re.compile(r'data-automation-id="[^"]*job', re.I), "workday"),
    (re.compile(r"icims\.com/jobs|iCIMS_JobsTable", re.I), "icims"),
    (re.compile(r'id="icims_content"', re.I), "icims"),
    (re.compile(r"greenhouse\.io|boards\.greenhouse\.io", re.I), "greenhouse"),
    (re.compile(r'"gh-header"|"greenhouse-job-board"', re.I), "greenhouse"),
    (re.compile(r"jobs\.lever\.co|lever\.co/[^/]+/jobs", re.I), "lever"),
    (re.compile(r'"lever-job-posting"', re.I), "lever"),
    (re.compile(r"taleo\.net", re.I), "taleo"),
    (re.compile(r"sap-talent|successfactors", re.I), "successfactors"),
    (re.compile(r"SmartRecruiters|smartrecruiters\.com", re.I), "smartrecruiters"),
]


def detect_from_url(url: str) -> Optional[str]:
    """Return ATS type based solely on URL pattern, or None."""
    for pattern, ats_type in _URL_PATTERNS:
        if pattern.search(url):
            return ats_type
    return None


async def detect_from_html(url: str, timeout: float = 10.0) -> Optional[str]:
    """
    Fetch the page with a lightweight GET and fingerprint the HTML.
    Returns ATS type string or None if unrecognised.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; JobMatcherBot/1.0; "
            "+https://github.com/your-repo/job-scraper)"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=timeout, headers=headers
        ) as client:
            resp = await client.get(url)
            html = resp.text
    except Exception:
        return None

    for pattern, ats_type in _HTML_FINGERPRINTS:
        if pattern.search(html):
            return ats_type
    return None


async def detect_ats(url: str) -> str:
    """
    Full detection pipeline: URL first, then HTML fetch.
    Always returns a string — falls back to "generic".
    """
    ats = detect_from_url(url)
    if ats:
        return ats
    ats = await detect_from_html(url)
    return ats or "generic"
