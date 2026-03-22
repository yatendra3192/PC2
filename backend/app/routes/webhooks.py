"""Webhook routes — receive callbacks from PIM and DQ systems."""

import json
import logging
from fastapi import APIRouter, Request, HTTPException
from app.db.client import fetch_one, execute

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/pim/status-update")
async def pim_status_update(request: Request):
    """PIM notifies PC2 when a submitted record is accepted/rejected."""
    body = await request.json()

    product_id = body.get("pc2_product_id")
    pim_status = body.get("pim_status")  # accepted | rejected
    rejection_reason = body.get("rejection_reason")

    if not product_id or not pim_status:
        raise HTTPException(status_code=400, detail="Missing pc2_product_id or pim_status")

    product = await fetch_one("SELECT id FROM products WHERE id = $1::uuid", product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if pim_status == "rejected":
        await execute(
            "UPDATE products SET status = 'rejected', updated_at = now() WHERE id = $1::uuid",
            product_id,
        )
    elif pim_status == "accepted":
        await execute(
            "UPDATE products SET status = 'published', updated_at = now() WHERE id = $1::uuid",
            product_id,
        )

    # Audit trail
    await execute(
        """INSERT INTO audit_trail (product_id, layer, action, new_value, actor_type, actor_id, reason)
           VALUES ($1::uuid, 'client', $2, $3, 'system', 'pim_webhook', $4)""",
        product_id,
        "published" if pim_status == "accepted" else "rejected",
        pim_status,
        rejection_reason,
    )

    logger.info(f"PIM status update: product {product_id} → {pim_status}")
    return {"received": True, "product_id": product_id, "status": pim_status}


@router.post("/dq/rule-update")
async def dq_rule_update(request: Request):
    """DQ notifies PC2 when validation rules change."""
    body = await request.json()
    logger.info(f"DQ rule update received: {json.dumps(body)[:200]}")

    # In production: refresh cached DQ rules, re-validate affected products
    await execute(
        """INSERT INTO audit_trail (layer, action, new_value, actor_type, actor_id)
           VALUES ('config', 'mapping_corrected', $1, 'system', 'dq_webhook')""",
        json.dumps(body)[:500],
    )

    return {"received": True}


@router.post("/dq/recheck")
async def dq_recheck(request: Request):
    """DQ requests re-check of specific products."""
    body = await request.json()
    product_ids = body.get("product_ids", [])

    logger.info(f"DQ recheck requested for {len(product_ids)} products")

    # Queue re-validation for each product
    for pid in product_ids:
        try:
            from app.tasks.batch_processor import run_single_stage
            run_single_stage.delay(pid, 5)  # Re-run Stage 5 validation
        except Exception:
            logger.warning(f"Could not queue recheck for {pid} — Celery may not be running")

    return {"received": True, "queued": len(product_ids)}
