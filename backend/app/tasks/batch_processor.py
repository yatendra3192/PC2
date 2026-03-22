"""Celery tasks for batch processing.

process_batch: parses file → creates product records → queues pipeline for each.
run_product_pipeline: runs full pipeline (all enabled stages) for one product.
"""

import json
import asyncio
import logging
from app.tasks import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code in sync Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="pc2.process_batch", max_retries=3)
def process_batch(self, batch_id: str):
    """Parse a batch file, create product records, queue pipeline for each."""
    logger.info(f"Processing batch {batch_id}")

    async def _process():
        from app.db.client import init_db, fetch_one, fetch_all, execute, execute_returning
        from app.parsers import parse_file

        await init_db()

        batch = await fetch_one("SELECT * FROM batches WHERE id = $1::uuid", batch_id)
        if not batch:
            logger.error(f"Batch {batch_id} not found")
            return

        client_id = str(batch["client_id"])
        file_path = batch["file_path"]
        file_type = batch["file_type"]

        # Update status
        await execute("UPDATE batches SET status = 'processing' WHERE id = $1::uuid", batch_id)

        try:
            # Parse file into product records
            records = await parse_file(file_path, file_type)
            logger.info(f"Parsed {len(records)} records from {file_path}")

            # Update item count
            await execute(
                "UPDATE batches SET item_count = $1 WHERE id = $2::uuid",
                len(records), batch_id,
            )

            # Get pipeline config for client
            client = await fetch_one("SELECT pipeline_config_id FROM clients WHERE id = $1::uuid", client_id)
            pipeline_config_id = str(client["pipeline_config_id"]) if client and client["pipeline_config_id"] else None

            # Create a product record for each parsed row
            product_ids = []
            for i, record in enumerate(records):
                # Extract identity fields if available
                product_name = record.get("Product Name") or record.get("product_name") or record.get("Name")
                model_number = record.get("Model") or record.get("model_number") or record.get("Model Number")
                sku = record.get("SKU") or record.get("sku")
                brand = record.get("Brand") or record.get("brand")
                supplier = record.get("Supplier") or record.get("supplier_name")

                row = await execute_returning(
                    """INSERT INTO products
                       (client_id, batch_id, product_name, model_number, sku, brand, supplier_name,
                        status, pipeline_config_id)
                       VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, 'draft', $8::uuid)
                       RETURNING id""",
                    client_id, batch_id, product_name, model_number, sku, brand, supplier,
                    pipeline_config_id,
                )
                product_id = str(row["id"])
                product_ids.append(product_id)

                # Store all raw fields from the parsed record
                for field_name, value in record.items():
                    if field_name.startswith("_"):
                        continue  # Skip internal fields
                    await execute_returning(
                        """INSERT INTO product_raw_values
                           (product_id, supplier_field_name, raw_value, source, source_cell_ref)
                           VALUES ($1::uuid, $2, $3, $4, $5)
                           RETURNING id""",
                        product_id, field_name, str(value),
                        record.get("_source", "csv"),
                        f"row:{record.get('_row_number', i + 1)}",
                    )

                # Update batch progress
                await execute(
                    "UPDATE batches SET processed_count = $1 WHERE id = $2::uuid",
                    i + 1, batch_id,
                )

            # Queue pipeline processing for each product
            for pid in product_ids:
                run_product_pipeline.delay(pid)

            # Mark batch complete
            await execute(
                "UPDATE batches SET status = 'complete', item_count = $1, processed_count = $1, completed_at = now() WHERE id = $2::uuid",
                len(records), batch_id,
            )

            logger.info(f"Batch {batch_id} complete: {len(records)} products created, pipelines queued")

        except Exception as e:
            logger.error(f"Batch {batch_id} failed: {e}")
            await execute(
                "UPDATE batches SET status = 'failed', error_message = $1 WHERE id = $2::uuid",
                str(e)[:500], batch_id,
            )
            raise

    _run_async(_process())


@celery_app.task(bind=True, name="pc2.run_product_pipeline", max_retries=2)
def run_product_pipeline(self, product_id: str):
    """Run the full pipeline for a single product (all enabled stages)."""
    logger.info(f"Running pipeline for product {product_id}")

    async def _run():
        from app.db.client import init_db, fetch_one
        from app.pipeline.orchestrator import run_pipeline

        # Ensure all stages are registered
        import app.pipeline.stage_1_ingest  # noqa: F401
        import app.pipeline.stage_2_classify  # noqa: F401
        import app.pipeline.stage_3_dedup  # noqa: F401
        import app.pipeline.stage_4_enrich  # noqa: F401
        import app.pipeline.stage_5_validate  # noqa: F401
        import app.pipeline.stage_6_transform  # noqa: F401
        import app.pipeline.stage_7_review  # noqa: F401

        await init_db()
        await run_pipeline(product_id)

    _run_async(_run())


@celery_app.task(name="pc2.run_single_stage")
def run_single_stage(product_id: str, stage_num: int):
    """Run a single stage for a product (used for re-processing)."""
    logger.info(f"Running stage {stage_num} for product {product_id}")

    async def _run():
        from app.db.client import init_db, fetch_one
        from app.pipeline.orchestrator import get_processor
        import json

        # Ensure stage is registered
        import app.pipeline.stage_1_ingest  # noqa: F401
        import app.pipeline.stage_2_classify  # noqa: F401
        import app.pipeline.stage_3_dedup  # noqa: F401
        import app.pipeline.stage_4_enrich  # noqa: F401
        import app.pipeline.stage_5_validate  # noqa: F401
        import app.pipeline.stage_6_transform  # noqa: F401
        import app.pipeline.stage_7_review  # noqa: F401

        await init_db()

        product = await fetch_one("SELECT pipeline_config_id FROM products WHERE id = $1::uuid", product_id)
        config_row = await fetch_one(
            "SELECT stage_configs FROM pipeline_configs WHERE id = $1::uuid",
            str(product["pipeline_config_id"]) if product and product["pipeline_config_id"] else None,
        )
        stage_configs = json.loads(config_row["stage_configs"]) if config_row and config_row["stage_configs"] else {}
        stage_config = stage_configs.get(str(stage_num), {})

        processor = get_processor(stage_num)
        await processor.process(product_id, stage_config)

    _run_async(_run())
