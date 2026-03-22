from __future__ import annotations
import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException

from app.db.client import fetch_all, fetch_one, execute_returning, execute
from app.auth.dependencies import get_current_user, require_admin
from app.models.user import TokenPayload
from app.models.batch import BatchResponse
from app.storage.client import save_upload

router = APIRouter()


@router.post("", response_model=BatchResponse)
async def upload_batch(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    async_process: bool = Form(True),
    user: TokenPayload = Depends(require_admin),
):
    """Upload a file and optionally start async batch processing via Celery."""
    # Determine file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "unknown"
    file_type_map = {"pdf": "pdf", "csv": "csv", "xlsx": "xlsx", "xls": "xlsx", "jpg": "image", "png": "image", "jpeg": "image"}
    file_type = file_type_map.get(ext, "csv")

    # Save file
    contents = await file.read()
    storage_path = await save_upload(contents, file.filename or "upload", client_id)

    # Get supplier template for this client (if exists)
    supplier_template = await fetch_one(
        "SELECT id FROM supplier_templates WHERE is_active = true ORDER BY created_at DESC LIMIT 1",
    )

    # Create batch record
    row = await execute_returning(
        """INSERT INTO batches (client_id, supplier_template_id, file_name, file_path, file_type, status, created_by)
           VALUES ($1::uuid, $2::uuid, $3, $4, $5, 'queued', $6::uuid)
           RETURNING *""",
        client_id,
        str(supplier_template["id"]) if supplier_template else None,
        file.filename, storage_path, file_type, user.sub,
    )

    batch_id = str(row["id"])

    # Queue async processing via Celery
    if async_process:
        try:
            from app.tasks.batch_processor import process_batch
            process_batch.delay(batch_id)
        except Exception as e:
            # Celery not running — fall back to sync processing
            import logging
            logging.getLogger(__name__).warning(f"Celery not available, falling back to sync: {e}")
            # Create single product for sync mode
            client = await fetch_one("SELECT pipeline_config_id FROM clients WHERE id = $1::uuid", client_id)
            pipeline_config_id = str(client["pipeline_config_id"]) if client and client["pipeline_config_id"] else None
            await execute_returning(
                """INSERT INTO products (client_id, batch_id, status, pipeline_config_id)
                   VALUES ($1::uuid, $2::uuid, 'draft', $3::uuid) RETURNING id""",
                client_id, batch_id, pipeline_config_id,
            )

    return _batch_from_row(row)


@router.get("", response_model=list[BatchResponse])
async def list_batches(
    status: str | None = None,
    user: TokenPayload = Depends(get_current_user),
):
    if status:
        rows = await fetch_all(
            "SELECT * FROM batches WHERE status = $1 ORDER BY created_at DESC LIMIT 50", status,
        )
    else:
        rows = await fetch_all("SELECT * FROM batches ORDER BY created_at DESC LIMIT 50")
    return [_batch_from_row(r) for r in rows]


@router.get("/{batch_id}")
async def get_batch(batch_id: str, user: TokenPayload = Depends(get_current_user)):
    """Get batch with all product items and their pipeline status."""
    row = await fetch_one("SELECT * FROM batches WHERE id = $1::uuid", batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Get all products in this batch with review counts
    products = await fetch_all(
        """SELECT p.id, p.product_name, p.model_number, p.current_stage, p.status,
                  p.completeness_pct, p.overall_confidence,
                  (SELECT COUNT(*) FROM product_iksula_values piv
                   WHERE piv.product_id = p.id AND piv.review_status IN ('needs_review','low_confidence')) as review_count
           FROM products p
           WHERE p.batch_id = $1::uuid
           ORDER BY p.created_at""",
        batch_id,
    )

    batch = _batch_from_row(row)
    return {
        **batch.model_dump(),
        "products": [
            {
                "id": str(p["id"]),
                "product_name": p["product_name"],
                "model_number": p["model_number"],
                "current_stage": p["current_stage"],
                "status": p["status"],
                "completeness_pct": p["completeness_pct"],
                "overall_confidence": p["overall_confidence"],
                "review_count": p["review_count"],
            }
            for p in products
        ],
    }


@router.post("/{batch_id}/process")
async def process_batch(batch_id: str, user: TokenPayload = Depends(require_admin)):
    """Trigger processing of a batch — runs Stage 1 on all products in the batch."""
    from app.pipeline.stage_1_ingest import stage1  # noqa: F811 — ensure registered

    batch = await fetch_one("SELECT * FROM batches WHERE id = $1::uuid", batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Update batch status
    await execute("UPDATE batches SET status = 'processing' WHERE id = $1::uuid", batch_id)

    # Get products in this batch
    products = await fetch_all("SELECT id FROM products WHERE batch_id = $1::uuid", batch_id)

    results = []
    for prod in products:
        product_id = str(prod["id"])
        # Get stage config
        product = await fetch_one("SELECT pipeline_config_id FROM products WHERE id = $1::uuid", product_id)
        config_row = await fetch_one("SELECT stage_configs FROM pipeline_configs WHERE id = $1::uuid", str(product["pipeline_config_id"])) if product["pipeline_config_id"] else None
        stage_configs = json.loads(config_row["stage_configs"]) if config_row and config_row["stage_configs"] else {}
        stage_1_config = stage_configs.get("1", {})

        result = await stage1.process(product_id, stage_1_config)
        results.append({
            "product_id": product_id,
            "status": result.status,
            "fields_found": result.metadata.get("fields_found", 0),
            "fields_missing": result.metadata.get("fields_missing", 0),
        })

    # Update batch
    await execute(
        "UPDATE batches SET status = 'complete', processed_count = $1, completed_at = now() WHERE id = $2::uuid",
        len(products), batch_id,
    )

    return {"batch_id": batch_id, "products_processed": len(results), "results": results}


def _batch_from_row(r) -> BatchResponse:
    return BatchResponse(
        id=str(r["id"]),
        client_id=str(r["client_id"]),
        file_name=r["file_name"],
        file_path=r["file_path"],
        file_type=r["file_type"],
        item_count=r["item_count"],
        processed_count=r["processed_count"] or 0,
        status=r["status"],
        error_message=r["error_message"],
        created_by=str(r["created_by"]) if r["created_by"] else None,
        created_at=r["created_at"],
        completed_at=r["completed_at"],
    )
