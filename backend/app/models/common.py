from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime
from typing import Any


class TimestampMixin(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConfidenceBreakdown(BaseModel):
    source_reliability: float = 0
    consistency: float = 0
    completeness: float = 0


class StageResult(BaseModel):
    stage: int
    status: str  # "complete" | "needs_review" | "failed"
    fields_processed: int = 0
    fields_needing_review: int = 0
    fields_auto_approved: int = 0
    fields_failed: int = 0
    output: dict[str, Any] = {}


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
