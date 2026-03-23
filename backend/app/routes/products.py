from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.client import fetch_all, fetch_one, execute
from app.auth.dependencies import get_current_user, require_reviewer
from app.models.user import TokenPayload
from app.models.product import ProductResponse, ProductDetailResponse, ProductIksulaValue, ProductRawValue

router = APIRouter()


@router.get("", response_model=list[ProductResponse])
async def list_products(
    status: str | None = None,
    batch_id: str | None = None,
    limit: int = Query(50, le=200),
    user: TokenPayload = Depends(get_current_user),
):
    conditions = []
    params = []
    idx = 1

    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    if batch_id:
        conditions.append(f"batch_id = ${idx}::uuid")
        params.append(batch_id)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    rows = await fetch_all(f"SELECT * FROM products {where} ORDER BY created_at DESC LIMIT ${idx}", *params)
    return [_product_from_row(r) for r in rows]


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(product_id: str, user: TokenPayload = Depends(get_current_user)):
    row = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get Layer 0 raw values
    raw_rows = await fetch_all(
        "SELECT * FROM product_raw_values WHERE product_id = $1::uuid ORDER BY extracted_at",
        product_id,
    )

    # Get Layer 1 Iksula values with attribute info
    iksula_rows = await fetch_all(
        """SELECT piv.*, ica.attribute_code, ica.attribute_name, ica.unit, ica.is_mandatory, ica.display_order
           FROM product_iksula_values piv
           JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
           WHERE piv.product_id = $1::uuid
           ORDER BY ica.display_order""",
        product_id,
    )

    product = _product_from_row(row)
    detail = ProductDetailResponse(**product.model_dump())

    detail.raw_values = [
        ProductRawValue(
            id=str(r["id"]),
            product_id=str(r["product_id"]),
            supplier_field_name=r["supplier_field_name"],
            raw_value=r["raw_value"],
            source=r["source"],
            source_url=r["source_url"],
            source_page_ref=r["source_page_ref"],
            extraction_model=r["extraction_model"],
            extraction_confidence=r["extraction_confidence"],
            mapped_to_attribute_id=str(r["mapped_to_attribute_id"]) if r["mapped_to_attribute_id"] else None,
        )
        for r in raw_rows
    ]

    detail.iksula_values = [
        ProductIksulaValue(
            id=str(r["id"]),
            product_id=str(r["product_id"]),
            attribute_id=str(r["attribute_id"]),
            attribute_code=r["attribute_code"],
            attribute_name=r["attribute_name"],
            unit=r["unit"],
            value_text=r["value_text"],
            value_numeric=float(r["value_numeric"]) if r["value_numeric"] is not None else None,
            value_boolean=r["value_boolean"],
            value_array=r["value_array"],
            source=r["source"],
            model_name=r["model_name"],
            raw_extracted=r["raw_extracted"],
            confidence=r["confidence"] or 0,
            confidence_breakdown=json.loads(r["confidence_breakdown"]) if r["confidence_breakdown"] else None,
            review_status=r["review_status"],
            set_at_stage=r["set_at_stage"],
        )
        for r in iksula_rows
    ]

    # Get Layer 2 client values
    client_rows = await fetch_all(
        """SELECT client_field_name, client_value, iksula_raw_value, transform_applied, review_status
           FROM product_client_values
           WHERE product_id = $1::uuid
           ORDER BY (SELECT client_field_order FROM client_field_mappings WHERE id = field_mapping_id)""",
        product_id,
    )
    detail.client_values = [
        {
            "client_field_name": r["client_field_name"],
            "client_value": r["client_value"],
            "iksula_raw_value": r["iksula_raw_value"],
            "transform_applied": r["transform_applied"],
            "review_status": r["review_status"] or "auto",
        }
        for r in client_rows
    ]

    return detail


@router.post("/{product_id}/advance")
async def advance_product(product_id: str, user: TokenPayload = Depends(require_reviewer)):
    """Approve current stage, advance to next, and run the pipeline from there."""
    # Ensure all stage processors are registered
    import app.pipeline.stage_1_ingest  # noqa: F401
    import app.pipeline.stage_2_classify  # noqa: F401
    import app.pipeline.stage_3_dedup  # noqa: F401
    import app.pipeline.stage_4_enrich  # noqa: F401
    import app.pipeline.stage_5_validate  # noqa: F401
    import app.pipeline.stage_6_transform  # noqa: F401
    import app.pipeline.stage_7_review  # noqa: F401
    from app.pipeline.orchestrator import run_pipeline

    product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    current = product["current_stage"]
    next_stage = current + 1

    if next_stage > 7:
        return {"message": "Product is at final stage", "current_stage": current}

    # Approve all pending fields at current stage
    await execute(
        """UPDATE product_iksula_values
           SET review_status = 'human_approved', updated_at = now()
           WHERE product_id = $1::uuid AND set_at_stage = $2
             AND review_status IN ('needs_review', 'low_confidence', 'pending')""",
        product_id, current,
    )

    # Advance to next stage
    await execute(
        "UPDATE products SET current_stage = $1, status = 'processing', updated_at = now() WHERE id = $2::uuid",
        next_stage, product_id,
    )

    # Run the pipeline from the next stage (will continue until review needed or complete)
    try:
        await run_pipeline(product_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Pipeline error after advance: {e}")

    # Get updated product state
    updated = await fetch_one("SELECT current_stage, status FROM products WHERE id = $1::uuid", product_id)
    return {
        "product_id": product_id,
        "advanced_to": updated["current_stage"] if updated else next_stage,
        "status": updated["status"] if updated else "processing",
    }


@router.post("/{product_id}/approve-all")
async def approve_all_fields(product_id: str, user: TokenPayload = Depends(require_reviewer)):
    """Approve all fields at the current stage."""
    product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await execute(
        """UPDATE product_iksula_values
           SET review_status = 'human_approved', updated_at = now()
           WHERE product_id = $1::uuid
             AND review_status IN ('needs_review', 'low_confidence', 'pending')""",
        product_id,
    )

    return {"message": "All fields approved", "product_id": product_id}


@router.patch("/{product_id}/fields/{attribute_code}")
async def edit_field(
    product_id: str,
    attribute_code: str,
    value: str,
    user: TokenPayload = Depends(require_reviewer),
):
    """Edit a single field value (inline edit)."""
    # Find the attribute
    attr = await fetch_one(
        "SELECT id FROM iksula_class_attributes WHERE attribute_code = $1", attribute_code,
    )
    if not attr:
        raise HTTPException(status_code=404, detail=f"Attribute {attribute_code} not found")

    # Update the value
    result = await fetch_one(
        """UPDATE product_iksula_values
           SET value_text = $1, source = 'human', review_status = 'human_edited',
               model_name = NULL, updated_at = now()
           WHERE product_id = $2::uuid AND attribute_id = $3::uuid
           RETURNING id""",
        value, product_id, str(attr["id"]),
    )

    if not result:
        raise HTTPException(status_code=404, detail="Field not found for this product")

    # Audit trail
    await execute(
        """INSERT INTO audit_trail (product_id, layer, field_name, stage, action, new_value, actor_type, actor_id)
           VALUES ($1::uuid, 'iksula', $2, NULL, 'edited', $3, 'human', $4)""",
        product_id, attribute_code, value, user.sub,
    )

    return {"message": "Field updated", "attribute_code": attribute_code, "new_value": value}


def _product_from_row(r) -> ProductResponse:
    return ProductResponse(
        id=str(r["id"]),
        client_id=str(r["client_id"]),
        batch_id=str(r["batch_id"]) if r["batch_id"] else None,
        taxonomy_node_id=str(r["taxonomy_node_id"]) if r["taxonomy_node_id"] else None,
        product_name=r["product_name"],
        model_number=r["model_number"],
        sku=r["sku"],
        upc=r["upc"],
        ean=r["ean"],
        brand=r["brand"],
        supplier_name=r["supplier_name"],
        current_stage=r["current_stage"] or 1,
        status=r["status"] or "draft",
        product_title=r["product_title"],
        short_description=r["short_description"],
        long_description=r["long_description"],
        overall_confidence=r["overall_confidence"],
        completeness_pct=r["completeness_pct"],
        stage_metadata=json.loads(r["stage_metadata"]) if r["stage_metadata"] else {},
        dq_results=json.loads(r["dq_results"]) if r["dq_results"] else {},
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        published_at=r["published_at"],
    )
