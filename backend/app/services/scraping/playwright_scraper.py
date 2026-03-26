"""
Phase 7: Playwright-based scraper for company career pages running on
Workday, iCIMS, SAP SuccessFactors, or custom ATS systems.
Stub implementation — fleshed out in Phase 7.
"""
from typing import Optional


async def scrape_workday_jobs(company_url: str, company_name: str) -> list[dict]:
    """
    Scrape jobs from a Workday career portal.
    Example URL: https://company.wd5.myworkdayjobs.com/en-US/External
    """
    from playwright.async_api import async_playwright

    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(company_url, wait_until="networkidle", timeout=30_000)

        # Workday renders job list in li[data-automation-id="jobFoundDescription"]
        items = await page.query_selector_all('[data-automation-id="jobFoundDescription"]')
        for item in items:
            title_el = await item.query_selector('[data-automation-id="jobTitle"]')
            location_el = await item.query_selector('[data-automation-id="locations"]')
            link_el = await item.query_selector("a")

            title = await title_el.inner_text() if title_el else ""
            location = await location_el.inner_text() if location_el else ""
            url = await link_el.get_attribute("href") if link_el else ""

            if title:
                jobs.append({
                    "source": "playwright_workday",
                    "external_id": url or title,
                    "company": company_name,
                    "title": title.strip(),
                    "location": location.strip(),
                    "is_remote": "remote" in location.lower(),
                    "url": url,
                    "description": "",
                })

        await browser.close()
    return jobs
