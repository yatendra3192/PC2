"""Pipeline routes — trigger individual stages on a product."""

import json
from fastapi import APIRouter, Depends, HTTPException

from app.db.client import fetch_one
from app.auth.dependencies import require_reviewer
from app.models.user import TokenPayload
from app.pipeline.orchestrator import get_processor

# Ensure all stage processors are registered
import app.pipeline.stage_1_ingest  # noqa: F401
import app.pipeline.stage_2_classify  # noqa: F401
import app.pipeline.stage_3_dedup  # noqa: F401
import app.pipeline.stage_4_enrich  # noqa: F401
import app.pipeline.stage_5_validate  # noqa: F401
import app.pipeline.stage_6_transform  # noqa: F401
import app.pipeline.stage_7_review  # noqa: F401

router = APIRouter()


@router.post("/{product_id}/run-stage/{stage_num}")
async def run_stage(
    product_id: str,
    stage_num: int,
    user: TokenPayload = Depends(require_reviewer),
):
    """Run a specific stage on a product."""
    product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        processor = get_processor(stage_num)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Stage {stage_num} not available yet")

    # Get stage config
    config_row = await fetch_one(
        "SELECT stage_configs FROM pipeline_configs WHERE id = $1::uuid",
        str(product["pipeline_config_id"]) if product["pipeline_config_id"] else None,
    )
    stage_configs = json.loads(config_row["stage_configs"]) if config_row and config_row["stage_configs"] else {}
    stage_config = stage_configs.get(str(stage_num), {})

    result = await processor.process(product_id, stage_config)

    return {
        "product_id": product_id,
        "stage": stage_num,
        "status": result.status,
        "fields_count": len(result.fields),
        "fields_needing_review": result.fields_needing_review,
        "fields_auto_approved": result.fields_auto_approved,
        "metadata": result.metadata,
    }
