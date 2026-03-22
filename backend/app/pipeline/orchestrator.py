import json
import logging

from app.db.client import fetch_one, execute
from app.pipeline.base import StageResult

logger = logging.getLogger(__name__)

# Stage processors are registered here
_processors: dict[int, "StageProcessor"] = {}


def register_processor(stage_num: int, processor):
    _processors[stage_num] = processor


def get_processor(stage_num: int):
    proc = _processors.get(stage_num)
    if not proc:
        raise ValueError(f"No processor registered for stage {stage_num}")
    return proc


async def run_pipeline(product_id: str):
    """Run the full pipeline for a product, stage by stage."""
    product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    # Get pipeline config
    config_row = await fetch_one(
        "SELECT * FROM pipeline_configs WHERE id = $1::uuid",
        str(product["pipeline_config_id"]) if product["pipeline_config_id"] else None,
    )

    stages_enabled = json.loads(config_row["stages_enabled"]) if config_row else {str(i): True for i in range(1, 8)}
    stage_configs = json.loads(config_row["stage_configs"]) if config_row and config_row["stage_configs"] else {}

    current_stage = product["current_stage"] or 1

    for stage_num in range(current_stage, 8):
        if not stages_enabled.get(str(stage_num), True):
            logger.info(f"Stage {stage_num} disabled, skipping")
            continue

        processor = _processors.get(stage_num)
        if not processor:
            logger.warning(f"No processor for stage {stage_num}, skipping")
            continue

        stage_config = stage_configs.get(str(stage_num), {})
        logger.info(f"Running stage {stage_num} for product {product_id}")

        # Update product status
        await execute(
            "UPDATE products SET current_stage = $1, status = 'processing', updated_at = now() WHERE id = $2::uuid",
            stage_num, product_id,
        )

        # Run the stage
        result: StageResult = await processor.process(product_id, stage_config)

        # Update product after stage
        new_status = "review" if result.has_review_items else "processing"
        stage_meta = json.dumps({str(stage_num): result.metadata}) if result.metadata else "{}"

        await execute(
            """UPDATE products
               SET current_stage = $1, status = $2,
                   stage_metadata = stage_metadata || $3::jsonb,
                   updated_at = now()
               WHERE id = $4::uuid""",
            stage_num, new_status, stage_meta, product_id,
        )

        # If review needed, pause the pipeline
        if result.has_review_items:
            logger.info(f"Stage {stage_num}: {result.fields_needing_review} fields need review, pausing pipeline")
            return result

    # All stages done
    await execute(
        "UPDATE products SET status = 'review', updated_at = now() WHERE id = $1::uuid",
        product_id,
    )
    logger.info(f"Pipeline complete for product {product_id}")
