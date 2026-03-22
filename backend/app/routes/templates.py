"""Template management routes — upload client templates, trigger AI auto-mapping, review mappings."""

from __future__ import annotations


import json
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.db.client import fetch_all, fetch_one, execute_returning
from app.auth.dependencies import require_admin, require_reviewer
from app.models.user import TokenPayload
from app.pipeline.auto_mapper import auto_map_template

router = APIRouter()


class TemplateCreateRequest(BaseModel):
    client_id: str
    template_name: str
    version: str
    export_formats: list[str] = ["csv"]


class AutoMapRequest(BaseModel):
    template_id: str
    taxonomy_node_id: str
    client_fields: list[dict]  # [{"name": "...", "code": "...", "sample_values": [...]}]


@router.get("")
async def list_templates(_: TokenPayload = Depends(require_reviewer)):
    rows = await fetch_all("SELECT * FROM retailer_templates ORDER BY last_updated DESC")
    return [_template_from_row(r) for r in rows]


@router.post("")
async def create_template(req: TemplateCreateRequest, user: TokenPayload = Depends(require_admin)):
    row = await execute_returning(
        """INSERT INTO retailer_templates (client_id, template_name, version, export_formats, maintained_by)
           VALUES ($1::uuid, $2, $3, $4, 'Iksula')
           RETURNING *""",
        req.client_id, req.template_name, req.version, req.export_formats,
    )
    return _template_from_row(row)


@router.post("/upload-and-map")
async def upload_template_and_auto_map(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    taxonomy_node_id: str = Form(...),
    template_name: str = Form(...),
    version: str = Form("1.0"),
    user: TokenPayload = Depends(require_admin),
):
    """Upload a client template file (CSV with headers), create template, and AI auto-map fields.

    The CSV file should have the client's column headers as the first row.
    Optionally, data rows provide sample values for better AI mapping.
    """
    contents = await file.read()
    text = contents.decode("utf-8-sig")

    # Parse CSV to extract headers + sample values
    reader = csv.reader(io.StringIO(text))
    rows_list = list(reader)

    if not rows_list:
        raise HTTPException(status_code=400, detail="Empty file")

    headers = rows_list[0]
    sample_data = rows_list[1:6]  # Use up to 5 data rows for sample values

    # Build client field definitions
    client_fields = []
    for i, header in enumerate(headers):
        header = header.strip()
        if not header:
            continue

        sample_values = []
        for data_row in sample_data:
            if i < len(data_row) and data_row[i].strip():
                sample_values.append(data_row[i].strip())

        client_fields.append({
            "name": header,
            "code": header.lower().replace(" ", "_").replace("(", "").replace(")", ""),
            "sample_values": list(set(sample_values)),  # Deduplicate
        })

    # Create template record
    template_row = await execute_returning(
        """INSERT INTO retailer_templates (client_id, template_name, version, export_formats, maintained_by)
           VALUES ($1::uuid, $2, $3, '{"csv"}', 'Client')
           RETURNING *""",
        client_id, template_name, version,
    )
    template_id = str(template_row["id"])

    # Run AI auto-mapping
    result = await auto_map_template(client_id, template_id, taxonomy_node_id, client_fields)

    return {
        "template": _template_from_row(template_row),
        "mapping_result": result,
        "client_fields_detected": len(client_fields),
        "message": f"Template created. {result['mapped']} fields auto-mapped, {result['unmapped']} need manual mapping. Please review in the mapping editor.",
    }


@router.get("/{template_id}/mappings")
async def get_template_mappings(template_id: str, taxonomy_node_id: str | None = None, _: TokenPayload = Depends(require_reviewer)):
    """Get all field mappings for a template, grouped by status."""
    conditions = ["cfm.template_id = $1::uuid"]
    params = [template_id]
    idx = 2

    if taxonomy_node_id:
        conditions.append(f"cfm.taxonomy_node_id = ${idx}::uuid")
        params.append(taxonomy_node_id)

    rows = await fetch_all(
        f"""SELECT cfm.*, ica.attribute_code, ica.attribute_name, ica.data_type, ica.unit, ica.is_mandatory
           FROM client_field_mappings cfm
           JOIN iksula_class_attributes ica ON cfm.iksula_attribute_id = ica.id
           WHERE {' AND '.join(conditions)}
           ORDER BY cfm.client_field_order""",
        *params,
    )

    auto_mapped = [r for r in rows if r["mapping_status"] == "auto"]
    corrected = [r for r in rows if r["mapping_status"] == "corrected"]
    manual = [r for r in rows if r["mapping_status"] == "manual"]
    unmapped = [r for r in rows if r["mapping_status"] == "unmapped"]

    return {
        "total": len(rows),
        "auto_mapped": len(auto_mapped),
        "corrected": len(corrected),
        "manual": len(manual),
        "unmapped": len(unmapped),
        "mappings": [
            {
                "id": str(r["id"]),
                "iksula_code": r["attribute_code"],
                "iksula_name": r["attribute_name"],
                "iksula_type": r["data_type"],
                "iksula_unit": r["unit"],
                "iksula_mandatory": r["is_mandatory"],
                "client_field": r["client_field_name"],
                "client_code": r["client_field_code"],
                "transform": json.loads(r["transform_rule"]) if isinstance(r["transform_rule"], str) else r["transform_rule"],
                "status": r["mapping_status"],
                "confidence": r.get("auto_map_confidence"),
            }
            for r in rows
        ],
    }


def _template_from_row(r) -> dict:
    return {
        "id": str(r["id"]),
        "client_id": str(r["client_id"]),
        "template_name": r["template_name"],
        "version": r["version"],
        "export_formats": r["export_formats"],
        "is_active": r["is_active"],
        "maintained_by": r["maintained_by"],
        "last_updated": str(r["last_updated"]) if r["last_updated"] else None,
    }
