from __future__ import annotations
from pydantic import BaseModel
from typing import Any


class SupplierFieldMapping(BaseModel):
    id: str
    supplier_template_id: str
    supplier_field_name: str
    supplier_field_alias: list[str] | None = None
    iksula_attribute_id: str | None = None
    normalise_rule: dict[str, Any] | None = None
    mapping_status: str = "auto"

    class Config:
        from_attributes = True


class ClientFieldMapping(BaseModel):
    id: str
    client_id: str
    template_id: str
    taxonomy_node_id: str
    iksula_attribute_id: str
    iksula_attribute_code: str | None = None  # joined
    iksula_attribute_name: str | None = None  # joined
    client_field_name: str
    client_field_code: str
    client_field_order: int = 0
    is_mandatory: bool = False
    char_limit: int | None = None
    transform_rule: dict[str, Any] = {"type": "direct"}
    mapping_status: str = "auto"

    class Config:
        from_attributes = True


class ClientFieldMappingUpdate(BaseModel):
    client_field_name: str | None = None
    client_field_code: str | None = None
    transform_rule: dict[str, Any] | None = None
    mapping_status: str | None = None


class ClientValueMapping(BaseModel):
    id: str
    client_field_mapping_id: str
    iksula_value_code: str
    iksula_value_label: str
    client_value: str
    mapping_status: str = "auto"

    class Config:
        from_attributes = True
