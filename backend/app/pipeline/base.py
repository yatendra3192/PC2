from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldProvenance:
    field_name: str
    value: Any
    source: str  # ocr, vision, csv, web_google, web_marketplace, kb, llm, human
    model_name: str | None = None
    prompt_template: str | None = None
    confidence: float = 0.0
    confidence_breakdown: dict | None = None
    raw_extracted: str | None = None
    source_url: str | None = None
    source_page_ref: str | None = None
    review_status: str = "pending"  # pending, auto_approved, needs_review, low_confidence
    alternatives: list[dict] | None = None


@dataclass
class StageResult:
    stage: int
    status: str  # complete, needs_review, failed
    fields: list[FieldProvenance] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def fields_needing_review(self) -> int:
        return sum(1 for f in self.fields if f.review_status in ("needs_review", "low_confidence"))

    @property
    def fields_auto_approved(self) -> int:
        return sum(1 for f in self.fields if f.review_status == "auto_approved")

    @property
    def has_review_items(self) -> bool:
        return self.fields_needing_review > 0


class StageProcessor(ABC):
    """Base interface for all pipeline stage processors."""

    stage_number: int
    stage_name: str

    @abstractmethod
    async def process(self, product_id: str, config: dict) -> StageResult:
        """Run this stage on a product. Return fields with provenance."""
        pass

    @abstractmethod
    def required_models(self) -> list[str]:
        """Which AI model capabilities does this stage need?"""
        pass
