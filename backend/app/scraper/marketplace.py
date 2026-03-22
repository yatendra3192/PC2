"""Marketplace scraping (Amazon, retailer sites) for attribute extraction.

Production: Playwright scrapes product pages, extracts from spec tables + bullets.
Demo: Returns hardcoded results from mock adapter.
"""

from __future__ import annotations


import logging
from app.config import settings

logger = logging.getLogger(__name__)


class MarketplaceScraper:
    def __init__(self, sources: list[str] | None = None, max_results: int = 10):
        self.sources = sources or ["amazon.com"]
        self.max_results = max_results

    async def search_and_scrape(self, product_name: str, model_number: str | None = None) -> list[dict]:
        """Search marketplace sites, scrape top N product pages."""
        if settings.demo_mode:
            return []  # Mock adapter handles demo data

        results = []
        for source in self.sources:
            try:
                source_results = await self._search_source(source, product_name, model_number)
                results.extend(source_results)
            except Exception as e:
                logger.warning(f"Failed to scrape {source}: {e}")

        return results[:self.max_results]

    async def _search_source(self, source: str, product_name: str, model_number: str | None) -> list[dict]:
        """Scrape a specific marketplace."""
        from playwright.async_api import async_playwright
        from app.scraper.extractor import AttributeExtractor

        query = f"{product_name} {model_number or ''}"

        if "amazon" in source:
            search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
        else:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}+site:{source}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(search_url, timeout=15000)
            html = await page.content()
            await browser.close()

        extractor = AttributeExtractor()
        return [{"url": search_url, "attrs": extractor.extract(html)}]
