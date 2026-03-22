"""File storage — local filesystem for demo, Supabase Storage for production."""

import os
import uuid
from pathlib import Path

UPLOAD_DIR = Path("/tmp/pc2_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def save_upload(file_bytes: bytes, filename: str, client_id: str) -> str:
    """Save an uploaded file and return the storage path."""
    ext = Path(filename).suffix
    stored_name = f"{client_id}/{uuid.uuid4()}{ext}"
    full_path = UPLOAD_DIR / stored_name
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(file_bytes)
    return str(stored_name)


def get_upload_path(storage_path: str) -> Path:
    return UPLOAD_DIR / storage_path
