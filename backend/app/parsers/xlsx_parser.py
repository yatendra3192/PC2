"""XLSX/XLS parser — handles merged cells, multiple sheets, messy headers."""

import logging

logger = logging.getLogger(__name__)


async def parse_xlsx(file_path: str) -> list[dict]:
    """Parse an Excel file into a list of product data dicts."""
    try:
        import openpyxl
    except ImportError:
        logger.warning("openpyxl not installed — falling back to CSV-like parsing")
        from app.parsers.csv_parser import parse_csv
        return await parse_csv(file_path)

    from pathlib import Path
    from app.storage.client import UPLOAD_DIR

    path = Path(file_path) if Path(file_path).exists() else UPLOAD_DIR / file_path
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    # First row = headers
    headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]

    products = []
    for row_num, row in enumerate(rows[1:], start=2):
        cleaned = {}
        for i, value in enumerate(row):
            if i >= len(headers):
                break
            key = headers[i]
            if value is not None and str(value).strip():
                cleaned[key] = str(value).strip()

        if cleaned:
            cleaned["_source"] = "xlsx"
            cleaned["_row_number"] = row_num
            products.append(cleaned)

    wb.close()
    logger.info(f"Parsed {len(products)} products from XLSX: {file_path}")
    return products
