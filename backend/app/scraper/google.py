"""Google search + URL scraping for attribute extraction.

Production: Uses SerpAPI for search, Playwright for JS-rendered pages.
Demo: Returns hardcoded results from mock adapter.
"""

import logging
from app.config import settings

logger = logging.getLogger(__name__)


class GoogleScraper:
    def __init__(self, max_urls: int = 3, timeout_ms: int = 10000):
        self.max_urls = max_urls
        self.timeout_ms = timeout_ms

    async def search_and_scrape(self, query: str) -> list[dict]:
        """Search Google, scrape top N URLs, extract product attributes."""
        if settings.demo_mode:
            return []  # Mock adapter handles demo data

        # Production flow:
        # 1. Search via SerpAPI
        urls = await self._search(query)

        # 2. Scrape each URL
        results = []
        for url in urls[:self.max_urls]:
            try:
                attrs = await self._scrape_url(url)
                results.append({"url": url, "attrs": attrs})
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")

        return results

    async def _search(self, query: str) -> list[str]:
        """Google search via SerpAPI."""
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://serpapi.com/search", params={
                "q": query,
                "api_key": settings.serpapi_key,
                "num": self.max_urls,
            })
            data = resp.json()
            return [r["link"] for r in data.get("organic_results", [])[:self.max_urls]]

    async def _scrape_url(self, url: str) -> dict:
        """Scrape a single URL using Playwright + BeautifulSoup."""
        from playwright.async_api import async_playwright
        from app.scraper.extractor import AttributeExtractor

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=self.timeout_ms)
            html = await page.content()
            await browser.close()

        return AttributeExtractor().extract(html)
