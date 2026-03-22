"""HIL Review routes — the core interface for cataloguers.

Provides:
- Review queue with filtering (priority, stage, confidence, batch)
- Bulk approve / reject
- Single field edit + approve
- Review summary stats
- Product review card (image + title + all attributes side by side)
"""

from __future__ import annotations


import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.client import fetch_all, fetch_one, execute, execute_returning
from app.auth.dependencies import get_current_user, require_reviewer
from app.models.user import TokenPayload

router = APIRouter()


# ── Request/Response Models ──

class ReviewItem(BaseModel):
    """One field needing review."""
    id: str
    product_id: str
    product_name: str | None
    model_number: str | None
    attribute_code: str
    attribute_name: str
    value: str | None
    unit: str | None
    source: str
    model_name: str | None
    confidence: float
    confidence_explanation: str | None
    review_status: str
    stage: int
    batch_name: str | None


class ReviewProductCard(BaseModel):
    """Side-by-side product review card for cataloguers."""
    product_id: str
    product_name: str | None
    model_number: str | None
    brand: str | None
    supplier_name: str | None
    image_url: str | None
    current_stage: int
    status: str
    completeness_pct: float | None
    product_title: str | None
    short_description: str | None
    long_description: str | None
    # All attributes in a flat list — easy for side-by-side display
    attributes: list[dict]
    # Only items needing action
    review_items: list[dict]
    # Summary
    total_fields: int
    auto_approved: int
    needs_review: int
    human_approved: int


class BulkApproveRequest(BaseModel):
    field_ids: list[str]


class BulkRejectRequest(BaseModel):
    field_ids: list[str]
    reason: str


class FieldEditRequest(BaseModel):
    value: str
    reason: str | None = None


class ReviewStats(BaseModel):
    total_pending: int
    must_fix: int
    low_confidence: int
    needs_review: int
    auto_approved: int
    human_approved: int
    human_edited: int


# ── Review Queue ──

@router.get("/queue", response_model=list[ReviewItem])
async def get_review_queue(
    priority: str | None = Query(None, description="must_fix | low_confidence | needs_review"),
    stage: int | None = Query(None, ge=1, le=7),
    confidence_min: float | None = Query(None, ge=0),
    confidence_max: float | None = Query(None, le=100),
    batch_id: str | None = None,
    product_id: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    user: TokenPayload = Depends(require_reviewer),
):
    """Get the review queue — filterable, sorted by priority."""
    conditions = ["piv.review_status IN ('needs_review', 'low_confidence', 'pending')"]
    params: list = []
    idx = 1

    if priority == "must_fix":
        conditions.append(f"piv.review_status = ${idx}")
        params.append("low_confidence")
        idx += 1
    elif priority == "low_confidence":
        conditions.append(f"piv.confidence < ${idx}")
        params.append(60.0)
        idx += 1
    elif priority == "needs_review":
        conditions.append(f"piv.review_status = ${idx}")
        params.append("needs_review")
        idx += 1

    if stage:
        conditions.append(f"piv.set_at_stage = ${idx}")
        params.append(stage)
        idx += 1

    if confidence_min is not None:
        conditions.append(f"piv.confidence >= ${idx}")
        params.append(confidence_min)
        idx += 1

    if confidence_max is not None:
        conditions.append(f"piv.confidence <= ${idx}")
        params.append(confidence_max)
        idx += 1

    if batch_id:
        conditions.append(f"p.batch_id = ${idx}::uuid")
        params.append(batch_id)
        idx += 1

    if product_id:
        conditions.append(f"p.id = ${idx}::uuid")
        params.append(product_id)
        idx += 1

    # Exclude published products
    conditions.append("p.status != 'published'")

    where = " AND ".join(conditions)
    params.extend([limit, offset])

    rows = await fetch_all(f"""
        SELECT piv.id, piv.product_id, p.product_name, p.model_number,
               ica.attribute_code, ica.attribute_name, ica.unit,
               COALESCE(piv.value_text, piv.value_numeric::text, piv.value_boolean::text,
                        array_to_string(piv.value_array, ', ')) as value,
               piv.source, piv.model_name, piv.confidence, piv.review_status,
               piv.set_at_stage as stage,
               b.file_name as batch_name
        FROM product_iksula_values piv
        JOIN products p ON piv.product_id = p.id
        JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
        LEFT JOIN batches b ON p.batch_id = b.id
        WHERE {where}
        ORDER BY
            CASE piv.review_status
                WHEN 'low_confidence' THEN 1
                WHEN 'needs_review' THEN 2
                WHEN 'pending' THEN 3
            END,
            piv.confidence ASC
        LIMIT ${idx} OFFSET ${idx + 1}
    """, *params)

    return [ReviewItem(
        id=str(r["id"]),
        product_id=str(r["product_id"]),
        product_name=r["product_name"],
        model_number=r["model_number"],
        attribute_code=r["attribute_code"],
        attribute_name=r["attribute_name"],
        value=r["value"],
        unit=r["unit"],
        source=r["source"],
        model_name=r["model_name"],
        confidence=r["confidence"] or 0,
        confidence_explanation=None,
        review_status=r["review_status"],
        stage=r["stage"],
        batch_name=r["batch_name"],
    ) for r in rows]


# ── Product Review Card (side-by-side view) ──

@router.get("/product/{product_id}", response_model=ReviewProductCard)
async def get_product_review_card(
    product_id: str,
    user: TokenPayload = Depends(require_reviewer),
):
    """Get full product card for side-by-side review — image + title + all attributes."""
    product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get all Iksula values with attribute info
    rows = await fetch_all("""
        SELECT piv.id, ica.attribute_code, ica.attribute_name, ica.unit,
               ica.is_mandatory, ica.attribute_group, ica.display_order,
               COALESCE(piv.value_text, piv.value_numeric::text, piv.value_boolean::text,
                        array_to_string(piv.value_array, ', ')) as display_value,
               piv.value_text, piv.value_numeric, piv.value_boolean, piv.value_array,
               piv.source, piv.model_name, piv.confidence, piv.review_status,
               piv.set_at_stage, piv.agreement_count, piv.raw_extracted,
               piv.confidence_breakdown
        FROM product_iksula_values piv
        JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
        WHERE piv.product_id = $1::uuid
        ORDER BY ica.display_order
    """, product_id)

    attributes = []
    review_items = []
    auto_count = 0
    review_count = 0
    human_count = 0

    for r in rows:
        attr = {
            "id": str(r["id"]),
            "code": r["attribute_code"],
            "name": r["attribute_name"],
            "value": r["display_value"],
            "unit": r["unit"],
            "group": r["attribute_group"],
            "mandatory": r["is_mandatory"],
            "source": r["source"],
            "model": r["model_name"],
            "confidence": r["confidence"] or 0,
            "status": r["review_status"],
            "stage": r["set_at_stage"],
            "agreement_count": r["agreement_count"] or 1,
            "raw_extracted": r["raw_extracted"],
        }
        attributes.append(attr)

        if r["review_status"] in ("auto_approved",):
            auto_count += 1
        elif r["review_status"] in ("human_approved", "human_edited"):
            human_count += 1
        elif r["review_status"] in ("needs_review", "low_confidence", "pending"):
            review_count += 1
            review_items.append(attr)

    return ReviewProductCard(
        product_id=str(product["id"]),
        product_name=product["product_name"],
        model_number=product["model_number"],
        brand=product["brand"],
        supplier_name=product["supplier_name"],
        image_url=None,  # TODO: fetch from storage
        current_stage=product["current_stage"] or 1,
        status=product["status"] or "draft",
        completeness_pct=product["completeness_pct"],
        product_title=product["product_title"],
        short_description=product["short_description"],
        long_description=product["long_description"],
        attributes=attributes,
        review_items=review_items,
        total_fields=len(attributes),
        auto_approved=auto_count,
        needs_review=review_count,
        human_approved=human_count,
    )


# ── Bulk Approve ──

@router.post("/approve")
async def bulk_approve(
    req: BulkApproveRequest,
    user: TokenPayload = Depends(require_reviewer),
):
    """Approve multiple fields at once."""
    if not req.field_ids:
        raise HTTPException(status_code=400, detail="No fields specified")

    approved = 0
    for field_id in req.field_ids:
        # Get current value for audit
        row = await fetch_one("""
            SELECT piv.id, piv.product_id, ica.attribute_code,
                   COALESCE(piv.value_text, piv.value_numeric::text) as value
            FROM product_iksula_values piv
            JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
            WHERE piv.id = $1::uuid
        """, field_id)
        if not row:
            continue

        await execute(
            """UPDATE product_iksula_values
               SET review_status = 'human_approved', updated_at = now()
               WHERE id = $1::uuid AND review_status NOT IN ('human_approved', 'human_edited')""",
            field_id,
        )

        # Audit trail
        await execute(
            """INSERT INTO audit_trail
               (product_id, layer, field_name, action, new_value, actor_type, actor_id)
               VALUES ($1::uuid, 'iksula', $2, 'approved', $3, 'human', $4)""",
            str(row["product_id"]), row["attribute_code"], row["value"], user.sub,
        )
        approved += 1

    return {"approved": approved, "total_requested": len(req.field_ids)}


# ── Bulk Reject ──

@router.post("/reject")
async def bulk_reject(
    req: BulkRejectRequest,
    user: TokenPayload = Depends(require_reviewer),
):
    """Reject multiple fields with a reason."""
    rejected = 0
    for field_id in req.field_ids:
        row = await fetch_one("""
            SELECT piv.id, piv.product_id, ica.attribute_code,
                   COALESCE(piv.value_text, piv.value_numeric::text) as value
            FROM product_iksula_values piv
            JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
            WHERE piv.id = $1::uuid
        """, field_id)
        if not row:
            continue

        await execute(
            "UPDATE product_iksula_values SET review_status = 'rejected', updated_at = now() WHERE id = $1::uuid",
            field_id,
        )

        await execute(
            """INSERT INTO audit_trail
               (product_id, layer, field_name, action, old_value, actor_type, actor_id, reason)
               VALUES ($1::uuid, 'iksula', $2, 'rejected', $3, 'human', $4, $5)""",
            str(row["product_id"]), row["attribute_code"], row["value"], user.sub, req.reason,
        )
        rejected += 1

    return {"rejected": rejected, "reason": req.reason}


# ── Single Field Edit + Approve ──

@router.post("/{field_id}/edit")
async def edit_and_approve(
    field_id: str,
    req: FieldEditRequest,
    user: TokenPayload = Depends(require_reviewer),
):
    """Edit a field value and approve it. Records old value in audit trail."""
    # Get current value
    row = await fetch_one("""
        SELECT piv.id, piv.product_id, piv.attribute_id, ica.attribute_code, ica.data_type,
               piv.value_text, piv.value_numeric, piv.value_boolean
        FROM product_iksula_values piv
        JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
        WHERE piv.id = $1::uuid
    """, field_id)
    if not row:
        raise HTTPException(status_code=404, detail="Field not found")

    old_value = row["value_text"] or (str(row["value_numeric"]) if row["value_numeric"] is not None else None) or (str(row["value_boolean"]) if row["value_boolean"] is not None else None)

    # Determine which column to update based on data type
    if row["data_type"] in ("integer", "decimal", "measurement"):
        try:
            numeric_val = float(req.value)
            await execute(
                """UPDATE product_iksula_values
                   SET value_numeric = $1, value_text = NULL, source = 'human',
                       review_status = 'human_edited', model_name = NULL, updated_at = now()
                   WHERE id = $2::uuid""",
                numeric_val, field_id,
            )
        except ValueError:
            await execute(
                """UPDATE product_iksula_values
                   SET value_text = $1, source = 'human',
                       review_status = 'human_edited', model_name = NULL, updated_at = now()
                   WHERE id = $2::uuid""",
                req.value, field_id,
            )
    elif row["data_type"] == "boolean":
        bool_val = req.value.lower() in ("true", "yes", "1")
        await execute(
            """UPDATE product_iksula_values
               SET value_boolean = $1, value_text = NULL, source = 'human',
                   review_status = 'human_edited', model_name = NULL, updated_at = now()
               WHERE id = $2::uuid""",
            bool_val, field_id,
        )
    else:
        await execute(
            """UPDATE product_iksula_values
               SET value_text = $1, source = 'human',
                   review_status = 'human_edited', model_name = NULL, updated_at = now()
               WHERE id = $2::uuid""",
            req.value, field_id,
        )

    # Audit trail with old + new value
    await execute(
        """INSERT INTO audit_trail
           (product_id, layer, field_name, action, old_value, new_value, actor_type, actor_id, reason)
           VALUES ($1::uuid, 'iksula', $2, 'edited', $3, $4, 'human', $5, $6)""",
        str(row["product_id"]), row["attribute_code"], old_value, req.value, user.sub, req.reason,
    )

    return {
        "field_id": field_id,
        "attribute_code": row["attribute_code"],
        "old_value": old_value,
        "new_value": req.value,
        "status": "human_edited",
    }


# ── Review Stats ──

@router.get("/stats", response_model=ReviewStats)
async def get_review_stats(user: TokenPayload = Depends(require_reviewer)):
    """Summary stats for the review dashboard."""
    row = await fetch_one("""
        SELECT
            COUNT(*) FILTER (WHERE piv.review_status IN ('needs_review','low_confidence','pending') AND p.status != 'published') as total_pending,
            COUNT(*) FILTER (WHERE piv.review_status = 'low_confidence' AND piv.confidence < 40 AND p.status != 'published') as must_fix,
            COUNT(*) FILTER (WHERE piv.review_status = 'low_confidence' AND p.status != 'published') as low_confidence,
            COUNT(*) FILTER (WHERE piv.review_status = 'needs_review' AND p.status != 'published') as needs_review,
            COUNT(*) FILTER (WHERE piv.review_status = 'auto_approved') as auto_approved,
            COUNT(*) FILTER (WHERE piv.review_status = 'human_approved') as human_approved,
            COUNT(*) FILTER (WHERE piv.review_status = 'human_edited') as human_edited
        FROM product_iksula_values piv
        JOIN products p ON piv.product_id = p.id
    """)

    return ReviewStats(
        total_pending=row["total_pending"] or 0,
        must_fix=row["must_fix"] or 0,
        low_confidence=row["low_confidence"] or 0,
        needs_review=row["needs_review"] or 0,
        auto_approved=row["auto_approved"] or 0,
        human_approved=row["human_approved"] or 0,
        human_edited=row["human_edited"] or 0,
    )
