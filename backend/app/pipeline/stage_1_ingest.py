"""Stage 1 — Raw Supplier Data Ingestion.

Takes uploaded file, extracts fields via OCR/CSV/Vision,
stores raw values (Layer 0), normalises to Iksula values (Layer 1).
"""

import json
import logging
from app.pipeline.base import StageProcessor, StageResult, FieldProvenance
from app.ai.router import invoke_model
from app.db.client import fetch_one, fetch_all, execute_returning

logger = logging.getLogger(__name__)

# Confidence thresholds (overridden by stage_config)
DEFAULT_AUTO_APPROVE = 90
DEFAULT_NEEDS_REVIEW = 65


class Stage1Ingest(StageProcessor):
    stage_number = 1
    stage_name = "Raw Supplier Data Ingestion"

    def required_models(self) -> list[str]:
        return ["pdf_extraction", "text_recognition"]

    async def process(self, product_id: str, config: dict) -> StageResult:
        auto_threshold = config.get("confidence", {}).get("auto_approve_threshold", DEFAULT_AUTO_APPROVE)
        review_threshold = config.get("confidence", {}).get("needs_review_threshold", DEFAULT_NEEDS_REVIEW)

        # Get product and its taxonomy class
        product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)

        # Load class-specific attribute definitions — this drives what fields to extract
        # The extraction model receives this list so it knows WHAT to look for
        target_attributes = []
        taxonomy_node_id = product["taxonomy_node_id"] if product else None
        if taxonomy_node_id:
            target_attributes = await fetch_all(
                """SELECT attribute_code, attribute_name, data_type, unit, is_mandatory, validation_rule
                   FROM iksula_class_attributes
                   WHERE taxonomy_node_id = $1::uuid ORDER BY display_order""",
                str(taxonomy_node_id),
            )
        else:
            # No taxonomy assigned yet — load all attributes from all classes
            # The AI model will match what it finds against available attribute definitions
            target_attributes = await fetch_all(
                """SELECT DISTINCT ON (attribute_code)
                   attribute_code, attribute_name, data_type, unit, is_mandatory, validation_rule
                   FROM iksula_class_attributes ORDER BY attribute_code, display_order""",
            )

        # Gather raw content from uploaded file (stored during batch upload)
        raw_values = await fetch_all(
            "SELECT supplier_field_name, raw_value FROM product_raw_values WHERE product_id = $1::uuid",
            product_id,
        )
        content_parts = [f"{rv['supplier_field_name']}: {rv['raw_value']}" for rv in raw_values if rv['raw_value']]
        content_str = "\n".join(content_parts) if content_parts else (product["product_name"] or "No content")

        # Pass target attributes + content to the AI model
        extraction = await invoke_model("extract_fields", {
            "product_id": product_id,
            "content": content_str,
            "product_name": product.get("product_name", ""),
            "target_attributes": [dict(a) for a in target_attributes] if target_attributes else [],
        })
        fields_data = extraction.value  # Dict of field_name -> {value, confidence, page}
        if not isinstance(fields_data, dict):
            logger.warning(f"Extraction returned non-dict: {type(fields_data)}, using empty")
            fields_data = {}

        # Store extracted fields
        result_fields = []
        identity_fields = {"product_name", "model_number", "supplier_name"}

        for field_name, field_data in fields_data.items():
            confidence = field_data.get("confidence", 0)
            value = field_data.get("value")
            page_ref = field_data.get("page")

            # Determine review status
            if confidence >= auto_threshold:
                review_status = "auto_approved"
            elif confidence >= review_threshold:
                review_status = "needs_review"
            else:
                review_status = "low_confidence"

            # Store in Layer 0 (raw)
            await execute_returning(
                """INSERT INTO product_raw_values
                   (product_id, supplier_field_name, raw_value, source,
                    source_page_ref, extraction_model, extraction_confidence)
                   VALUES ($1::uuid, $2, $3, 'ocr', $4, $5, $6)
                   RETURNING id""",
                product_id, field_name, str(value), page_ref,
                extraction.model_name, confidence,
            )

            # Update identity fields on product record
            if field_name == "product_name":
                await execute_returning(
                    "UPDATE products SET product_name = $1, updated_at = now() WHERE id = $2::uuid RETURNING id",
                    value, product_id,
                )
            elif field_name == "model_number":
                await execute_returning(
                    "UPDATE products SET model_number = $1, updated_at = now() WHERE id = $2::uuid RETURNING id",
                    value, product_id,
                )
            elif field_name == "supplier_name":
                await execute_returning(
                    "UPDATE products SET supplier_name = $1, updated_at = now() WHERE id = $2::uuid RETURNING id",
                    value, product_id,
                )

            # Store in Layer 1 (Iksula normalised) — map field to attribute
            attr_row = await fetch_one(
                "SELECT id FROM iksula_class_attributes WHERE attribute_code = $1",
                field_name,
            )
            if attr_row and field_name not in identity_fields:
                # Determine which value column to use
                numeric = field_data.get("numeric")
                boolean = field_data.get("boolean")
                val_text = str(value) if not numeric and boolean is None else None

                await execute_returning(
                    """INSERT INTO product_iksula_values
                       (product_id, attribute_id, value_text, value_numeric, value_boolean,
                        source, model_name, raw_extracted, confidence,
                        confidence_breakdown, review_status, set_at_stage)
                       VALUES ($1::uuid, $2::uuid, $3, $4, $5,
                               'raw_normalised', $6, $7, $8,
                               $9::jsonb, $10, 1)
                       ON CONFLICT (product_id, attribute_id) DO UPDATE SET
                         value_text = EXCLUDED.value_text,
                         value_numeric = EXCLUDED.value_numeric,
                         value_boolean = EXCLUDED.value_boolean,
                         confidence = EXCLUDED.confidence,
                         review_status = EXCLUDED.review_status,
                         updated_at = now()
                       RETURNING id""",
                    product_id, str(attr_row["id"]),
                    val_text, numeric, boolean,
                    extraction.model_name, str(value), confidence,
                    json.dumps({"source_reliability": confidence, "consistency": confidence, "completeness": 100}),
                    review_status,
                )

            result_fields.append(FieldProvenance(
                field_name=field_name,
                value=value,
                source="ocr",
                model_name=extraction.model_name,
                confidence=confidence,
                source_page_ref=page_ref,
                review_status=review_status,
            ))

        # Add blank fields that were NOT found (will enrich in Stage 4)
        # Re-read taxonomy_node_id in case it was updated
        product_updated = await fetch_one("SELECT taxonomy_node_id FROM products WHERE id = $1::uuid", product_id)
        tn_id = str(product_updated["taxonomy_node_id"]) if product_updated and product_updated["taxonomy_node_id"] else None
        if tn_id:
            all_attrs = await fetch_all(
                """SELECT attribute_code, attribute_name, is_mandatory
                   FROM iksula_class_attributes
                   WHERE taxonomy_node_id = $1::uuid
                   ORDER BY display_order""",
                tn_id,
            )
        else:
            all_attrs = []
        found_codes = set(fields_data.keys())
        for attr in all_attrs:
            if attr["attribute_code"] not in found_codes:
                result_fields.append(FieldProvenance(
                    field_name=attr["attribute_code"],
                    value=None,
                    source="not_found",
                    confidence=0,
                    review_status="pending",
                ))

        # Calculate completeness
        total = len(all_attrs)
        found = sum(1 for f in result_fields if f.value is not None)
        completeness = round((found / total) * 100, 1) if total > 0 else 0

        await execute_returning(
            "UPDATE products SET completeness_pct = $1, updated_at = now() WHERE id = $2::uuid RETURNING id",
            completeness, product_id,
        )

        return StageResult(
            stage=1,
            status="complete" if not any(f.review_status in ("needs_review", "low_confidence") for f in result_fields if f.value) else "needs_review",
            fields=result_fields,
            metadata={
                "model": extraction.model_name,
                "fields_found": found,
                "fields_missing": total - found,
                "completeness_pct": completeness,
            },
        )


# Register
from app.pipeline.orchestrator import register_processor
stage1 = Stage1Ingest()
register_processor(1, stage1)
