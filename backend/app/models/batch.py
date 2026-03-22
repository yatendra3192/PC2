from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime


class BatchCreate(BaseModel):
    client_id: str
    file_name: str
    file_type: str


class BatchResponse(BaseModel):
    id: str
    client_id: str
    file_name: str
    file_path: str
    file_type: str
    item_count: int | None = None
    processed_count: int = 0
    status: str = "queued"
    error_message: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True
