"""
Discover additional Greenhouse company board tokens by scraping the
Greenhouse job board directory. Run once to expand the company list.

Usage:
    cd backend
    python ../scripts/seed_greenhouse_companies.py
"""
import httpx
import re

# Greenhouse maintains a public list of boards
# This script fetches the first N pages of the directory
BASE = "https://boards.greenhouse.io"


def discover_tokens():
    tokens = set()
    with httpx.Client(headers={"User-Agent": "JobMatcher/1.0"}) as client:
        # The directory is at https://boards.greenhouse.io/
        resp = client.get(BASE, timeout=15)
        # Greenhouse board tokens appear in anchor hrefs: /company-name
        found = re.findall(r'href="/([a-z0-9_-]+)"', resp.text)
        tokens.update(found)

    # Filter out navigation links and keep plausible company tokens
    noise = {"login", "privacy", "terms", "accessibility", "api"}
    clean = sorted(t for t in tokens if t not in noise and len(t) > 2)
    print(f"Found {len(clean)} tokens")
    for t in clean:
        print(t)
    return clean


if __name__ == "__main__":
    discover_tokens()
