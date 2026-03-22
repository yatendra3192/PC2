from __future__ import annotations
from pydantic import BaseModel
from typing import Any


class TaxonomyNode(BaseModel):
    id: str
    parent_id: str | None = None
    level: str
    code: str
    name: str
    full_path: str
    children: list["TaxonomyNode"] = []

    class Config:
        from_attributes = True


class IksulaClassAttribute(BaseModel):
    id: str
    taxonomy_node_id: str
    attribute_code: str
    attribute_name: str
    attribute_group: str | None = None
    data_type: str
    unit: str | None = None
    is_mandatory: bool = False
    display_order: int = 0
    description: str | None = None
    validation_rule: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class IksulaAllowedValue(BaseModel):
    id: str
    attribute_id: str
    value_code: str
    value_label: str
    synonyms: list[str] | None = None

    class Config:
        from_attributes = True
