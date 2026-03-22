from __future__ import annotations
from pydantic import BaseModel
from typing import Any
from datetime import datetime


class PipelineConfig(BaseModel):
    id: str
    client_id: str
    name: str
    stages_enabled: dict[str, bool]
    stage_configs: dict[str, Any] = {}
    dq_config: dict[str, Any] = {}
    scraper_config: dict[str, Any] = {}

    class Config:
        from_attributes = True


class ModelRegistryEntry(BaseModel):
    id: str
    model_name: str
    model_type: str
    provider: str
    endpoint_url: str | None = None
    capabilities: list[str] = []
    default_for_stages: list[int] = []
    is_active: bool = True
    added_by: str = "iksula"
    client_id: str | None = None

    class Config:
        from_attributes = True


class RetailerTemplate(BaseModel):
    id: str
    client_id: str
    template_name: str
    version: str
    export_formats: list[str] = ["csv"]
    is_active: bool = True
    maintained_by: str = "Iksula"
    last_updated: datetime | None = None

    class Config:
        from_attributes = True


class AuditEntry(BaseModel):
    id: str
    product_id: str | None = None
    layer: str | None = None
    field_name: str | None = None
    stage: int | None = None
    action: str
    old_value: str | None = None
    new_value: str | None = None
    actor_type: str
    actor_id: str | None = None
    model_name: str | None = None
    reason: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
