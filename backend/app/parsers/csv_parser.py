"""CSV parser — handles messy headers, encoding issues, delimiter detection."""

import csv
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def parse_csv(file_path: str) -> list[dict]:
    """Parse a CSV file into a list of product data dicts."""
    path = Path(file_path)
    if not path.exists():
        # Try in uploads dir
        from app.storage.client import UPLOAD_DIR
        path = UPLOAD_DIR / file_path

    content = path.read_text(encoding="utf-8-sig", errors="replace")

    # Detect delimiter
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(content[:2048])
    except csv.Error:
        dialect = csv.excel  # Default to comma

    reader = csv.DictReader(io.StringIO(content), dialect=dialect)

    products = []
    for row_num, row in enumerate(reader):
        # Clean headers and values
        cleaned = {}
        for key, value in row.items():
            if key is None:
                continue
            clean_key = key.strip().strip('\ufeff')  # Remove BOM
            clean_value = value.strip() if value else None
            if clean_key and clean_value:
                cleaned[clean_key] = clean_value

        if cleaned:
            cleaned["_source"] = "csv"
            cleaned["_row_number"] = row_num + 2  # +2 for header + 0-index
            products.append(cleaned)

    logger.info(f"Parsed {len(products)} products from CSV: {file_path}")
    return products
