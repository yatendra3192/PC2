"""Celery tasks for web scraping — runs in background to avoid blocking the pipeline."""

from __future__ import annotations


import asyncio
import logging
from app.tasks import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="pc2.scrape_for_product", max_retries=2, soft_time_limit=60)
def scrape_for_product(product_id: str, product_name: str, model_number: str | None = None):
    """Scrape Google + marketplaces for a product's attributes."""
    logger.info(f"Scraping for product {product_id}: {product_name}")

    async def _scrape():
        from app.db.client import init_db, execute_returning
        from app.scraper.google import GoogleScraper
        from app.scraper.marketplace import MarketplaceScraper
        from app.scraper.extractor import AttributeExtractor

        await init_db()

        query = f"{product_name} {model_number or ''} specifications".strip()
        all_results = []

        # Google scrape
        try:
            google = GoogleScraper(max_urls=3, timeout_ms=10000)
            google_results = await google.search_and_scrape(query)
            for r in google_results:
                # Store each scraped attribute as a raw value
                for attr_name, attr_value in r.get("attrs", {}).items():
                    await execute_returning(
                        """INSERT INTO product_raw_values
                           (product_id, supplier_field_name, raw_value, source, source_url, extraction_model)
                           VALUES ($1::uuid, $2, $3, 'web_google', $4, 'Iksula Web Scraper v1.0')
                           RETURNING id""",
                        product_id, attr_name, str(attr_value), r["url"],
                    )
            all_results.extend(google_results)
        except Exception as e:
            logger.error(f"Google scrape failed: {e}")

        # Marketplace scrape
        try:
            marketplace = MarketplaceScraper(max_results=10)
            mkt_results = await marketplace.search_and_scrape(product_name, model_number)
            for r in mkt_results:
                for attr_name, attr_value in r.get("attrs", {}).items():
                    await execute_returning(
                        """INSERT INTO product_raw_values
                           (product_id, supplier_field_name, raw_value, source, source_url, extraction_model)
                           VALUES ($1::uuid, $2, $3, 'web_marketplace', $4, 'Iksula Web Scraper v1.0')
                           RETURNING id""",
                        product_id, attr_name, str(attr_value), r.get("url", ""),
                    )
            all_results.extend(mkt_results)
        except Exception as e:
            logger.error(f"Marketplace scrape failed: {e}")

        logger.info(f"Scrape complete for {product_id}: {len(all_results)} sources, {sum(len(r.get('attrs', {})) for r in all_results)} attributes")
        return len(all_results)

    return _run_async(_scrape())
