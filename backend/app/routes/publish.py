"""Publish + Export routes — final step of the pipeline."""

import csv
import io
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db.client import fetch_one, fetch_all, execute
from app.auth.dependencies import require_reviewer
from app.models.user import TokenPayload

router = APIRouter()


class PublishRequest(BaseModel):
    target: str = "staging"  # staging | production


@router.post("/{product_id}/publish")
async def publish_product(
    product_id: str,
    req: PublishRequest,
    user: TokenPayload = Depends(require_reviewer),
):
    """Publish a product to the retailer's PIM (staging or production)."""
    product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check all fields are resolved
    unresolved = await fetch_one(
        """SELECT COUNT(*) as cnt FROM product_iksula_values
           WHERE product_id = $1::uuid AND review_status IN ('needs_review', 'low_confidence')""",
        product_id,
    )
    if unresolved and unresolved["cnt"] > 0:
        raise HTTPException(status_code=400, detail=f"{unresolved['cnt']} fields still need review before publishing")

    # Get client info
    client = await fetch_one("SELECT * FROM clients WHERE id = $1::uuid", str(product["client_id"]))
    template = await fetch_one(
        "SELECT * FROM retailer_templates WHERE client_id = $1::uuid AND is_active = true LIMIT 1",
        str(product["client_id"]),
    )

    # Update product status
    await execute(
        """UPDATE products
           SET status = 'published', published_at = now(), updated_at = now()
           WHERE id = $1::uuid""",
        product_id,
    )

    # Audit trail
    await execute(
        """INSERT INTO audit_trail
           (product_id, layer, action, actor_type, actor_id, metadata)
           VALUES ($1::uuid, 'client', 'published', 'human', $2, $3::jsonb)""",
        product_id, user.sub,
        json.dumps({
            "target": req.target,
            "client": client["name"] if client else None,
            "template": template["template_name"] if template else None,
        }),
    )

    # In production: push to PIM API here
    # await pim_connector.push(product_id, req.target)

    return {
        "product_id": product_id,
        "status": "published",
        "target": req.target,
        "client": client["name"] if client else None,
        "template": template["template_name"] if template else None,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "message": f"Record published to {client['name'] if client else 'unknown'} {req.target} catalog",
    }


@router.get("/{product_id}/export")
async def export_product(
    product_id: str,
    format: str = "csv",
    user: TokenPayload = Depends(require_reviewer),
):
    """Export product in client template format."""
    product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get Layer 2 client values
    client_values = await fetch_all(
        """SELECT pcv.client_field_name, COALESCE(pcv.edited_value, pcv.client_value) as value
           FROM product_client_values pcv
           WHERE pcv.product_id = $1::uuid
           ORDER BY (SELECT cfm.client_field_order FROM client_field_mappings cfm WHERE cfm.id = pcv.field_mapping_id)""",
        product_id,
    )

    if not client_values:
        # Fallback to Iksula values
        client_values = await fetch_all(
            """SELECT ica.attribute_name as client_field_name,
                      COALESCE(piv.value_text, piv.value_numeric::text, piv.value_boolean::text,
                               array_to_string(piv.value_array, ', ')) as value
               FROM product_iksula_values piv
               JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
               WHERE piv.product_id = $1::uuid
               ORDER BY ica.display_order""",
            product_id,
        )

    if format == "json":
        data = {cv["client_field_name"]: cv["value"] for cv in client_values}
        data["_product_name"] = product["product_name"]
        data["_model_number"] = product["model_number"]
        return data

    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        headers = [cv["client_field_name"] for cv in client_values]
        values = [cv["value"] for cv in client_values]
        writer.writerow(headers)
        writer.writerow(values)
        output.seek(0)

        filename = f"{product['model_number'] or product_id}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    elif format == "xml":
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<product>']
        xml_lines.append(f'  <product_name>{product["product_name"] or ""}</product_name>')
        xml_lines.append(f'  <model_number>{product["model_number"] or ""}</model_number>')
        for cv in client_values:
            tag = cv["client_field_name"].lower().replace(" ", "_").replace("(", "").replace(")", "")
            xml_lines.append(f'  <{tag}>{cv["value"] or ""}</{tag}>')
        xml_lines.append('</product>')

        return StreamingResponse(
            iter(["\n".join(xml_lines)]),
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename={product['model_number'] or product_id}.xml"},
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
