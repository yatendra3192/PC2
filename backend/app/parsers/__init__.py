"""File parsers — extract product records from uploaded files."""

from app.parsers.csv_parser import parse_csv
from app.parsers.xlsx_parser import parse_xlsx
from app.parsers.pdf_parser import parse_pdf


async def parse_file(file_path: str, file_type: str) -> list[dict]:
    """Parse an uploaded file and return a list of product data dicts."""
    if file_type == "csv":
        return await parse_csv(file_path)
    elif file_type in ("xlsx", "xls"):
        return await parse_xlsx(file_path)
    elif file_type == "pdf":
        return await parse_pdf(file_path)
    elif file_type == "image":
        # Image files are single-product — return one record with image path
        return [{"_source": "image", "_file_path": file_path}]
    else:
        return [{"_source": file_type, "_file_path": file_path}]
