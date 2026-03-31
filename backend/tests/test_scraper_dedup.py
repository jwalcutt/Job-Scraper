"""Tests for scraper company list deduplication (Bug 2 regression coverage).

After the fix, LEVER_COMPANIES and GREENHOUSE_COMPANIES must contain no
duplicate slugs and must not be empty. The previous broken dedup one-liner
silently emptied the lists, causing zero jobs to be fetched.
"""
from app.services.scraping.greenhouse_scraper import GREENHOUSE_COMPANIES
from app.services.scraping.lever_scraper import LEVER_COMPANIES


class TestLeverCompaniesDedup:
    def test_list_is_not_empty(self):
        assert len(LEVER_COMPANIES) > 0, "LEVER_COMPANIES must not be empty"

    def test_no_duplicates(self):
        seen = set()
        dupes = []
        for slug in LEVER_COMPANIES:
            if slug in seen:
                dupes.append(slug)
            seen.add(slug)
        assert dupes == [], f"Duplicate Lever slugs found: {dupes}"

    def test_known_companies_present(self):
        # Sanity-check that well-known slugs survived dedup
        for slug in ("netflix", "lyft", "shopify"):
            assert slug in LEVER_COMPANIES, f"Expected '{slug}' in LEVER_COMPANIES"

    def test_list_length_preserved_after_dedup(self):
        # The deduplicated list must have the same length as a fresh set
        assert len(LEVER_COMPANIES) == len(set(LEVER_COMPANIES))


class TestGreenhouseCompaniesDedup:
    def test_list_is_not_empty(self):
        assert len(GREENHOUSE_COMPANIES) > 0, "GREENHOUSE_COMPANIES must not be empty"

    def test_no_duplicates(self):
        seen = set()
        dupes = []
        for token in GREENHOUSE_COMPANIES:
            if token in seen:
                dupes.append(token)
            seen.add(token)
        assert dupes == [], f"Duplicate Greenhouse tokens found: {dupes}"

    def test_known_companies_present(self):
        for token in ("anthropic", "stripe", "databricks"):
            assert token in GREENHOUSE_COMPANIES, (
                f"Expected '{token}' in GREENHOUSE_COMPANIES"
            )

    def test_list_length_preserved_after_dedup(self):
        assert len(GREENHOUSE_COMPANIES) == len(set(GREENHOUSE_COMPANIES))
