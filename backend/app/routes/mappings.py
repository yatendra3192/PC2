"""Mapping routes — view/edit field and value mappings between layers."""

from __future__ import annotations


import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.client import fetch_all, fetch_one, execute, execute_returning
from app.auth.dependencies import require_reviewer, require_admin
from app.models.user import TokenPayload

router = APIRouter()


class MappingUpdateRequest(BaseModel):
    client_field_name: str | None = None
    client_field_code: str | None = None
    transform_rule: dict | None = None


class ValueMappingRequest(BaseModel):
    iksula_value_code: str
    iksula_value_label: str
    client_value: str


@router.get("/{client_id}/{taxonomy_node_id}")
async def get_mappings(client_id: str, taxonomy_node_id: str, _: TokenPayload = Depends(require_reviewer)):
    """Get all field mappings for a class + client."""
    rows = await fetch_all(
        """SELECT cfm.*, ica.attribute_code, ica.attribute_name, ica.data_type, ica.unit, ica.is_mandatory
           FROM client_field_mappings cfm
           JOIN iksula_class_attributes ica ON cfm.iksula_attribute_id = ica.id
           WHERE cfm.client_id = $1::uuid AND cfm.taxonomy_node_id = $2::uuid
           ORDER BY cfm.client_field_order""",
        client_id, taxonomy_node_id,
    )
    return [_mapping_from_row(r) for r in rows]


@router.put("/{mapping_id}")
async def update_mapping(mapping_id: str, req: MappingUpdateRequest, user: TokenPayload = Depends(require_reviewer)):
    """Correct or update a field mapping."""
    updates = []
    params = []
    idx = 1

    if req.client_field_name is not None:
        updates.append(f"client_field_name = ${idx}")
        params.append(req.client_field_name)
        idx += 1
    if req.client_field_code is not None:
        updates.append(f"client_field_code = ${idx}")
        params.append(req.client_field_code)
        idx += 1
    if req.transform_rule is not None:
        updates.append(f"transform_rule = ${idx}::jsonb")
        params.append(json.dumps(req.transform_rule))
        idx += 1

    updates.append(f"mapping_status = 'corrected'")
    updates.append(f"mapped_by = ${idx}::uuid")
    params.append(user.sub)
    idx += 1
    updates.append("mapped_at = now()")
    updates.append("updated_at = now()")

    params.append(mapping_id)
    row = await execute_returning(
        f"UPDATE client_field_mappings SET {', '.join(updates)} WHERE id = ${idx}::uuid RETURNING *",
        *params,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Mapping not found")

    # Audit trail
    await execute(
        """INSERT INTO audit_trail (layer, field_name, action, new_value, actor_type, actor_id, reason)
           VALUES ('mapping', $1, 'mapping_corrected', $2, 'human', $3, 'Field mapping updated')""",
        row["client_field_name"], json.dumps(req.model_dump(exclude_none=True)), user.sub,
    )

    return {"message": "Mapping updated", "mapping_id": mapping_id}


@router.post("/{mapping_id}/value-map")
async def add_value_mapping(mapping_id: str, req: ValueMappingRequest, user: TokenPayload = Depends(require_reviewer)):
    """Add or update a value mapping."""
    row = await execute_returning(
        """INSERT INTO client_value_mappings
           (client_field_mapping_id, iksula_value_code, iksula_value_label, client_value, mapping_status, mapped_by, mapped_at)
           VALUES ($1::uuid, $2, $3, $4, 'manual', $5::uuid, now())
           ON CONFLICT (client_field_mapping_id, iksula_value_code) DO UPDATE SET
             client_value = EXCLUDED.client_value, mapping_status = 'corrected',
             mapped_by = EXCLUDED.mapped_by, mapped_at = now()
           RETURNING id""",
        mapping_id, req.iksula_value_code, req.iksula_value_label, req.client_value, user.sub,
    )
    return {"message": "Value mapping saved", "id": str(row["id"])}


@router.get("/{client_id}/unmapped")
async def get_unmapped(client_id: str, _: TokenPayload = Depends(require_reviewer)):
    """Get all Iksula attributes that have no mapping for this client."""
    rows = await fetch_all(
        """SELECT ica.attribute_code, ica.attribute_name, ica.is_mandatory, tn.name as class_name
           FROM iksula_class_attributes ica
           JOIN taxonomy_nodes tn ON ica.taxonomy_node_id = tn.id
           LEFT JOIN client_field_mappings cfm ON ica.id = cfm.iksula_attribute_id
             AND cfm.client_id = $1::uuid
           WHERE cfm.id IS NULL
           ORDER BY ica.is_mandatory DESC, tn.name, ica.display_order""",
        client_id,
    )
    return [dict(r) for r in rows]


def _mapping_from_row(r) -> dict:
    return {
        "id": str(r["id"]),
        "iksula_attribute_code": r["attribute_code"],
        "iksula_attribute_name": r["attribute_name"],
        "iksula_data_type": r["data_type"],
        "iksula_unit": r["unit"],
        "iksula_mandatory": r["is_mandatory"],
        "client_field_name": r["client_field_name"],
        "client_field_code": r["client_field_code"],
        "client_field_order": r["client_field_order"],
        "transform_rule": json.loads(r["transform_rule"]) if isinstance(r["transform_rule"], str) else r["transform_rule"],
        "mapping_status": r["mapping_status"],
    }
