"""HTML → structured product attributes extractor.

Parses spec tables, bullet points, JSON-LD structured data, key-value divs.
"""

from bs4 import BeautifulSoup
import json
import re
import logging

logger = logging.getLogger(__name__)


class AttributeExtractor:
    def extract(self, html: str) -> dict:
        """Extract product attributes from HTML page."""
        soup = BeautifulSoup(html, "html.parser")
        attrs = {}

        # 1. JSON-LD structured data (most reliable)
        attrs.update(self._extract_jsonld(soup))

        # 2. Specification tables
        attrs.update(self._extract_spec_tables(soup))

        # 3. Key-value divs/spans
        attrs.update(self._extract_key_value_pairs(soup))

        # 4. Bullet points
        attrs.update(self._extract_bullets(soup))

        return attrs

    def _extract_jsonld(self, soup: BeautifulSoup) -> dict:
        """Extract from schema.org JSON-LD."""
        attrs = {}
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    if "name" in data:
                        attrs["product_name"] = data["name"]
                    if "weight" in data:
                        attrs["weight"] = str(data["weight"])
                    if "color" in data:
                        attrs["color"] = data["color"]
                    if "brand" in data:
                        brand = data["brand"]
                        attrs["brand"] = brand.get("name", str(brand)) if isinstance(brand, dict) else str(brand)
            except (json.JSONDecodeError, TypeError):
                continue
        return attrs

    def _extract_spec_tables(self, soup: BeautifulSoup) -> dict:
        """Extract from HTML tables that look like spec tables."""
        attrs = {}
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value and len(key) < 60:
                        attrs[key.lower().replace(" ", "_")] = value
        return attrs

    def _extract_key_value_pairs(self, soup: BeautifulSoup) -> dict:
        """Extract from dt/dd pairs and label/value divs."""
        attrs = {}
        for dl in soup.find_all("dl"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                key = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                if key and value:
                    attrs[key.lower().replace(" ", "_")] = value
        return attrs

    def _extract_bullets(self, soup: BeautifulSoup) -> dict:
        """Extract attributes mentioned in bullet point lists."""
        attrs = {}
        patterns = [
            (r"(?:weighs?|weight)[:\s]+(.+?)(?:\.|$)", "weight"),
            (r"(\d+)\s*(?:zone|station)s?", "zones"),
            (r"(IP\d{2})", "ip_rating"),
            (r"(?:voltage|volts?)[:\s]+(\d+\s*V)", "voltage"),
            (r"(?:warranty|guaranteed)[:\s]+(.+?)(?:\.|$)", "warranty"),
        ]

        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            for pattern, attr_name in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    attrs[attr_name] = match.group(1).strip()

        return attrs
