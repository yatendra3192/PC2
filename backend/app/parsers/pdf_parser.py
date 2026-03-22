"""PDF parser — extracts text via OCR/AI, returns as single product record.

PDFs are typically spec sheets for a single product.
The text is passed to the AI extraction model in Stage 1.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def parse_pdf(file_path: str) -> list[dict]:
    """Parse a PDF file — extract raw text for AI processing."""
    from app.storage.client import UPLOAD_DIR

    path = Path(file_path) if Path(file_path).exists() else UPLOAD_DIR / file_path

    text = ""
    try:
        # Try PyPDF2 first (no OCR, just text extraction)
        import pypdf
        reader = pypdf.PdfReader(str(path))
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            text += f"\n--- Page {page_num + 1} ---\n{page_text}"
    except ImportError:
        logger.warning("pypdf not installed — PDF text extraction unavailable")
        text = f"[PDF file: {path.name} — text extraction requires pypdf]"
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        text = f"[PDF parsing failed: {e}]"

    # PDF = single product, text goes to AI for field extraction
    return [{
        "_source": "pdf",
        "_file_path": str(file_path),
        "_content": text,
        "_page_count": len(text.split("--- Page")) - 1,
    }]
