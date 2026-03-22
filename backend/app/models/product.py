from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime
from typing import Any


class ProductBase(BaseModel):
    product_name: str | None = None
    model_number: str | None = None
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    brand: str | None = None
    supplier_name: str | None = None


class ProductCreate(ProductBase):
    client_id: str
    batch_id: str | None = None


class ProductResponse(ProductBase):
    id: str
    client_id: str
    batch_id: str | None = None
    taxonomy_node_id: str | None = None
    current_stage: int = 1
    status: str = "draft"
    product_title: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    overall_confidence: float | None = None
    completeness_pct: float | None = None
    stage_metadata: dict[str, Any] = {}
    dq_results: dict[str, Any] = {}
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_at: datetime | None = None

    class Config:
        from_attributes = True


class ProductRawValue(BaseModel):
    id: str | None = None
    product_id: str
    supplier_field_name: str
    raw_value: str | None = None
    source: str
    source_url: str | None = None
    source_page_ref: str | None = None
    extraction_model: str | None = None
    extraction_confidence: float | None = None
    mapped_to_attribute_id: str | None = None


class ProductIksulaValue(BaseModel):
    id: str | None = None
    product_id: str
    attribute_id: str
    attribute_code: str | None = None  # joined from iksula_class_attributes
    attribute_name: str | None = None  # joined
    unit: str | None = None  # joined
    value_text: str | None = None
    value_numeric: float | None = None
    value_boolean: bool | None = None
    value_array: list[str] | None = None
    source: str
    model_name: str | None = None
    raw_extracted: str | None = None
    confidence: float = 0
    confidence_breakdown: dict | None = None
    confidence_explanation: str | None = None  # Human-readable: "94% because..."
    confidence_factors: list[str] | None = None  # Bullet points explaining each component
    all_sources: list[dict] | None = None
    sources_agree: bool | None = None
    agreement_count: int = 1
    review_status: str = "pending"
    set_at_stage: int = 1


class ProductClientValue(BaseModel):
    id: str | None = None
    product_id: str
    client_id: str
    client_field_name: str
    client_value: str
    iksula_raw_value: str | None = None
    transform_applied: str | None = None
    review_status: str = "auto"
    edited_value: str | None = None


class ProductDetailResponse(ProductResponse):
    raw_values: list[ProductRawValue] = []
    iksula_values: list[ProductIksulaValue] = []
    client_values: list[ProductClientValue] = []
