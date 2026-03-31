"""
Playwright-based scrapers for ATS career portals that require JavaScript rendering.

Supports:
  - Workday  (myworkdayjobs.com)
  - iCIMS    (icims.com portals)
  - Generic  (CSS/XPath heuristics for unknown ATS)

Rate-limiting: callers should enforce ≥5 s between requests per domain.
robots.txt compliance is checked before scraping.
"""
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

_BOT_UA = (
    "Mozilla/5.0 (compatible; JobMatcherBot/1.0; "
    "+https://github.com/your-repo/job-scraper)"
)

# ─────────────────────────────────────────────────────────────────────────────
# robots.txt helper
# ─────────────────────────────────────────────────────────────────────────────


async def _can_fetch(url: str) -> bool:
    """Return True if robots.txt permits our bot UA to fetch *url*."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(robots_url, headers={"User-Agent": _BOT_UA})
        rp = RobotFileParser()
        rp.parse(resp.text.splitlines())
        return rp.can_fetch(_BOT_UA, url)
    except Exception:
        # If we can't fetch robots.txt, assume allowed
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Workday scraper
# ─────────────────────────────────────────────────────────────────────────────


async def scrape_workday_jobs(careers_url: str, company_name: str) -> list[dict]:
    """
    Scrape all pages of a Workday career portal.

    Handles infinite-scroll / "Load more" pagination by watching for the
    "Load more jobs" button rendered by Workday.
    """
    if not await _can_fetch(careers_url):
        logger.warning("robots.txt disallows scraping %s", careers_url)
        return []

    from playwright.async_api import async_playwright

    jobs: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent=_BOT_UA)
        page = await context.new_page()

        try:
            await page.goto(careers_url, wait_until="networkidle", timeout=30_000)

            # Click "Load more jobs" until it disappears (pagination)
            while True:
                try:
                    load_more = page.locator('[data-automation-id="loadMoreButton"]')
                    if await load_more.is_visible(timeout=3_000):
                        await load_more.click()
                        await page.wait_for_load_state("networkidle", timeout=10_000)
                    else:
                        break
                except Exception:
                    break

            items = await page.query_selector_all('[data-automation-id="jobFoundDescription"]')
            for item in items:
                title_el = await item.query_selector('[data-automation-id="jobTitle"]')
                location_el = await item.query_selector('[data-automation-id="locations"]')
                link_el = await item.query_selector("a")

                title = (await title_el.inner_text()).strip() if title_el else ""
                location = (await location_el.inner_text()).strip() if location_el else ""
                href = await link_el.get_attribute("href") if link_el else ""

                if not title:
                    continue

                # Workday hrefs are relative paths like /en-US/External/job/…
                if href and not href.startswith("http"):
                    parsed = urlparse(careers_url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"

                jobs.append({
                    "source": "playwright_workday",
                    "external_id": href or f"{company_name}::{title}",
                    "company": company_name,
                    "title": title,
                    "location": location,
                    "is_remote": "remote" in location.lower(),
                    "url": href,
                    "description": "",
                })

        except Exception as exc:
            logger.error("Workday scrape failed for %s: %s", careers_url, exc)
        finally:
            await browser.close()

    logger.info("Workday %s (%s): %d jobs", company_name, careers_url, len(jobs))
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# iCIMS scraper
# ─────────────────────────────────────────────────────────────────────────────


async def scrape_icims_jobs(careers_url: str, company_name: str) -> list[dict]:
    """
    Scrape an iCIMS career portal.

    iCIMS portals render jobs in a table/list under #iCIMS_JobsTable.
    Some portals use infinite scroll; others use page-based navigation.
    """
    if not await _can_fetch(careers_url):
        logger.warning("robots.txt disallows scraping %s", careers_url)
        return []

    from playwright.async_api import async_playwright

    jobs: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent=_BOT_UA)
        page = await context.new_page()

        try:
            await page.goto(careers_url, wait_until="networkidle", timeout=30_000)

            page_num = 1
            while True:
                # iCIMS job rows have class iCIMS_JobsTable or data-icims attributes
                rows = await page.query_selector_all(
                    "#iCIMS_JobsTable .iCIMS_Anchor, "
                    ".iCIMS_JobsTable a[data-field='jobtitle'], "
                    "a.iCIMS-job-title"
                )

                for row in rows:
                    title = (await row.inner_text()).strip()
                    href = await row.get_attribute("href") or ""
                    if not href.startswith("http"):
                        href = urljoin(careers_url, href)

                    # Try to get location from sibling
                    location = ""
                    try:
                        parent = await row.evaluate_handle("el => el.closest('tr, .iCIMS_JobsTableRow')")
                        loc_el = await parent.query_selector(".iCIMS_JobsTableLocation, td:nth-child(2)")
                        if loc_el:
                            location = (await loc_el.inner_text()).strip()
                    except Exception:
                        pass

                    if title:
                        jobs.append({
                            "source": "playwright_icims",
                            "external_id": href or f"{company_name}::{title}",
                            "company": company_name,
                            "title": title,
                            "location": location,
                            "is_remote": "remote" in location.lower(),
                            "url": href,
                            "description": "",
                        })

                # Try to click "Next" page
                try:
                    next_btn = page.locator(
                        "a.iCIMS_Pager_Next, "
                        "a[aria-label='Next page'], "
                        ".pagination .next a"
                    )
                    if await next_btn.is_visible(timeout=2_000):
                        await next_btn.click()
                        await page.wait_for_load_state("networkidle", timeout=10_000)
                        page_num += 1
                    else:
                        break
                except Exception:
                    break

        except Exception as exc:
            logger.error("iCIMS scrape failed for %s: %s", careers_url, exc)
        finally:
            await browser.close()

    logger.info("iCIMS %s (%s): %d jobs", company_name, careers_url, len(jobs))
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Generic fallback scraper
# ─────────────────────────────────────────────────────────────────────────────

# Common CSS patterns that career pages use for job listing items
_GENERIC_JOB_SELECTORS = [
    "a[data-job-id]",
    "a[data-job-slug]",
    ".job-listing a",
    ".careers-list a",
    "li.job a",
    "tr.job-row td a",
    ".opening a",
    "[class*='job'][class*='title'] a",
    "h2.job-title a",
    "h3.job-title a",
]

_GENERIC_LOCATION_SELECTORS = [
    "[class*='location']",
    "[class*='Location']",
    ".job-location",
    "span.city",
]


async def scrape_generic_jobs(careers_url: str, company_name: str) -> list[dict]:
    """
    Best-effort scraper for unrecognised ATS platforms.
    Uses a battery of CSS heuristics to find job title links.
    """
    if not await _can_fetch(careers_url):
        logger.warning("robots.txt disallows scraping %s", careers_url)
        return []

    from playwright.async_api import async_playwright

    jobs: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent=_BOT_UA)
        page = await context.new_page()

        try:
            await page.goto(careers_url, wait_until="networkidle", timeout=30_000)

            for selector in _GENERIC_JOB_SELECTORS:
                links = await page.query_selector_all(selector)
                if len(links) >= 3:  # must find at least 3 matches to trust the selector
                    for link in links:
                        title = (await link.inner_text()).strip()
                        href = await link.get_attribute("href") or ""
                        if not href.startswith("http"):
                            href = urljoin(careers_url, href)

                        # Attempt to find nearby location text
                        location = ""
                        try:
                            parent = await link.evaluate_handle(
                                "el => el.closest('li, tr, div, article')"
                            )
                            for loc_sel in _GENERIC_LOCATION_SELECTORS:
                                loc_el = await parent.query_selector(loc_sel)
                                if loc_el:
                                    location = (await loc_el.inner_text()).strip()
                                    break
                        except Exception:
                            pass

                        if title and len(title) < 200:
                            jobs.append({
                                "source": "playwright_generic",
                                "external_id": href or f"{company_name}::{title}",
                                "company": company_name,
                                "title": title,
                                "location": location,
                                "is_remote": "remote" in location.lower(),
                                "url": href,
                                "description": "",
                            })
                    break  # stop after first working selector

        except Exception as exc:
            logger.error("Generic scrape failed for %s: %s", careers_url, exc)
        finally:
            await browser.close()

    # Deduplicate by external_id
    seen: set[str] = set()
    unique: list[dict] = []
    for job in jobs:
        if job["external_id"] not in seen:
            seen.add(job["external_id"])
            unique.append(job)

    logger.info("Generic %s (%s): %d jobs", company_name, careers_url, len(unique))
    return unique


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────────────


async def scrape_career_page(
    careers_url: str,
    company_name: str,
    ats_type: Optional[str] = None,
) -> list[dict]:
    """
    Dispatch to the correct Playwright scraper based on ats_type.
    If ats_type is None, auto-detects via ats_detector.
    """
    if ats_type is None:
        from app.services.scraping.ats_detector import detect_ats
        ats_type = await detect_ats(careers_url)

    if ats_type == "workday":
        return await scrape_workday_jobs(careers_url, company_name)
    elif ats_type == "icims":
        return await scrape_icims_jobs(careers_url, company_name)
    elif ats_type in ("greenhouse", "lever"):
        # These have dedicated API scrapers — skip Playwright
        logger.info("Skipping Playwright for %s (%s) — use API scraper", company_name, ats_type)
        return []
    else:
        return await scrape_generic_jobs(careers_url, company_name)
