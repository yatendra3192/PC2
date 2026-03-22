"""Stage 4 — Enrichment.

Fills attribute gaps using 4 sources in sequence:
1. Iksula KB (picklist + attribute dictionary)
2. LLM inference (category-specific prompt)
3. Web scrape — Google (top 3 URLs)
4. Web scrape — Marketplace (Amazon top 10)

Also generates copy (title, short description, long description).
Calculates completeness before/after.
"""

import json
import logging
from app.pipeline.base import StageProcessor, StageResult, FieldProvenance
from app.pipeline.confidence import stage4_enrichment_confidence
from app.ai.router import invoke_model
from app.db.client import fetch_one, fetch_all, execute_returning, execute

logger = logging.getLogger(__name__)

DEFAULT_AUTO_APPROVE = 85
DEFAULT_NEEDS_REVIEW = 60

# Source reliability defaults
SOURCE_RELIABILITY = {
    "kb": 95, "raw_normalised": 85, "vision": 75,
    "llm": 65, "web_google": 70, "web_marketplace": 65, "human": 100,
}


class Stage4Enrich(StageProcessor):
    stage_number = 4
    stage_name = "Enrichment"

    def required_models(self) -> list[str]:
        return ["attribute_lookup", "attribute_inference", "copy_generation", "web_enrichment"]

    async def process(self, product_id: str, config: dict) -> StageResult:
        auto_threshold = config.get("confidence", {}).get("auto_approve_threshold", DEFAULT_AUTO_APPROVE)
        review_threshold = config.get("confidence", {}).get("needs_review_threshold", DEFAULT_NEEDS_REVIEW)
        source_scores = config.get("confidence", {}).get("source_reliability_scores", SOURCE_RELIABILITY)

        product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
        taxonomy_node_id = str(product["taxonomy_node_id"]) if product["taxonomy_node_id"] else None

        # Get all class attributes
        all_attrs = await fetch_all(
            """SELECT id, attribute_code, attribute_name, data_type, unit, is_mandatory
               FROM iksula_class_attributes
               WHERE taxonomy_node_id = $1::uuid ORDER BY display_order""",
            taxonomy_node_id,
        ) if taxonomy_node_id else []

        # Get existing values (from Stage 1)
        existing = await fetch_all(
            "SELECT attribute_id, confidence FROM product_iksula_values WHERE product_id = $1::uuid",
            product_id,
        )
        existing_attr_ids = {str(r["attribute_id"]) for r in existing}

        # Calculate completeness BEFORE enrichment
        total_mandatory = sum(1 for a in all_attrs if a["is_mandatory"])
        found_before = sum(1 for a in all_attrs if a["is_mandatory"] and str(a["id"]) in existing_attr_ids)
        completeness_before = round((found_before / total_mandatory) * 100, 1) if total_mandatory > 0 else 0

        # Find missing attributes
        missing_attrs = [a for a in all_attrs if str(a["id"]) not in existing_attr_ids]

        # ── ENRICHMENT: Call 4 sources ──

        # Source 1 & 2: KB + LLM (returned together from mock)
        enrich_result = await invoke_model("enrich", {
            "product_id": product_id,
            "missing_attributes": [a["attribute_code"] for a in missing_attrs],
        })
        enriched_fields = enrich_result.value  # Dict of attr_code -> {value, source, confidence, model, ...}

        # Source 3 & 4: Web scrape (Google + Amazon)
        scrape_result = await invoke_model("web_scrape", {
            "product_id": product_id,
            "product_name": product["product_name"],
            "model_number": product["model_number"],
        })
        web_data = scrape_result.value  # {google_results: [...], amazon_results: [...]}

        # Store enriched values
        result_fields = []

        for attr in all_attrs:
            attr_id = str(attr["id"])
            attr_code = attr["attribute_code"]

            if attr_id in existing_attr_ids:
                # Already has value from Stage 1 — skip
                continue

            enriched = enriched_fields.get(attr_code)
            if not enriched:
                continue

            source = enriched.get("source", "llm")
            raw_value = enriched.get("raw", str(enriched.get("value", "")))
            source_url = enriched.get("url")
            model_name = enriched.get("model", enrich_result.model_name)

            # Determine value columns based on data type
            value = enriched["value"]
            val_text = None
            val_numeric = None
            val_boolean = None
            val_array = None

            if isinstance(value, list):
                val_array = value
            elif isinstance(value, bool):
                val_boolean = value
            elif isinstance(value, (int, float)):
                val_numeric = float(value)
            else:
                val_text = str(value)

            # Calculate confidence with full breakdown
            source_rel = source_scores.get(source, 60)
            picklist_match = enriched.get("confidence", 70)
            # Check if multiple web sources found this value
            agreement = 1
            if attr_code in _count_web_agreements(web_data, attr_code):
                agreement = _count_web_agreements(web_data, attr_code)[attr_code]
            multi_source_score = min(100, 50 + agreement * 15)

            conf = stage4_enrichment_confidence(source_rel, picklist_match, multi_source_score)

            review_status = (
                "auto_approved" if conf.composite >= auto_threshold
                else "needs_review" if conf.composite >= review_threshold
                else "low_confidence"
            )

            # Store in Layer 0 (raw)
            raw_id_row = await execute_returning(
                """INSERT INTO product_raw_values
                   (product_id, supplier_field_name, raw_value, source, source_url, extraction_model, extraction_confidence, mapped_to_attribute_id)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::uuid)
                   RETURNING id""",
                product_id, attr_code, raw_value, source, source_url, model_name, conf.composite, attr_id,
            )

            # Store in Layer 1 (Iksula normalised)
            await execute_returning(
                """INSERT INTO product_iksula_values
                   (product_id, attribute_id, value_text, value_numeric, value_boolean, value_array,
                    source, source_raw_value_ids, model_name, raw_extracted, confidence,
                    confidence_breakdown, review_status, set_at_stage, agreement_count, sources_agree)
                   VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6,
                           $7, $8, $9, $10, $11,
                           $12::jsonb, $13, 4, $14, $15)
                   ON CONFLICT (product_id, attribute_id) DO UPDATE SET
                     value_text = EXCLUDED.value_text, value_numeric = EXCLUDED.value_numeric,
                     value_boolean = EXCLUDED.value_boolean, value_array = EXCLUDED.value_array,
                     source = EXCLUDED.source, confidence = EXCLUDED.confidence,
                     confidence_breakdown = EXCLUDED.confidence_breakdown,
                     review_status = EXCLUDED.review_status, updated_at_stage = 4, updated_at = now()
                   RETURNING id""",
                product_id, attr_id, val_text, val_numeric, val_boolean, val_array,
                source,
                [str(raw_id_row["id"])] if raw_id_row else None,
                model_name, raw_value, conf.composite,
                json.dumps(conf.breakdown),
                review_status, agreement, agreement > 1,
            )

            result_fields.append(FieldProvenance(
                field_name=attr_code,
                value=value,
                source=source,
                model_name=model_name,
                confidence=conf.composite,
                confidence_breakdown=conf.breakdown,
                source_url=source_url,
                raw_extracted=raw_value,
                review_status=review_status,
                alternatives=[{"explanation": f} for f in conf.factors],
            ))

        # ── COPY GENERATION ──
        copy_result = await invoke_model("generate_copy", {
            "product_id": product_id,
            "product_name": product["product_name"],
            "model_number": product["model_number"],
        })
        copy_data = copy_result.value

        await execute(
            """UPDATE products SET
                 product_title = $1, short_description = $2, long_description = $3,
                 updated_at = now()
               WHERE id = $4::uuid""",
            copy_data.get("product_title"), copy_data.get("short_description"),
            copy_data.get("long_description"), product_id,
        )

        # Calculate completeness AFTER enrichment
        updated_existing = await fetch_all(
            "SELECT attribute_id FROM product_iksula_values WHERE product_id = $1::uuid", product_id,
        )
        updated_ids = {str(r["attribute_id"]) for r in updated_existing}
        found_after = sum(1 for a in all_attrs if a["is_mandatory"] and str(a["id"]) in updated_ids)
        completeness_after = round((found_after / total_mandatory) * 100, 1) if total_mandatory > 0 else 0

        await execute(
            "UPDATE products SET completeness_pct = $1, updated_at = now() WHERE id = $2::uuid",
            completeness_after, product_id,
        )

        return StageResult(
            stage=4,
            status="needs_review" if any(f.review_status != "auto_approved" for f in result_fields) else "complete",
            fields=result_fields,
            metadata={
                "model": enrich_result.model_name,
                "completeness_before": completeness_before,
                "completeness_after": completeness_after,
                "fields_enriched": len(result_fields),
                "copy_generated": True,
                "copy": copy_data,
                "copy_prompt": copy_result.metadata.get("prompt_template") if copy_result.metadata else None,
                "web_scrape": web_data,
                "models_used": [
                    {"model": "Iksula KB v3.1", "role": "Attribute lookup"},
                    {"model": "GPT-4o", "role": "Copy generation + inference"},
                    {"model": "Iksula Vision v1.2", "role": "Image analysis"},
                    {"model": "Iksula Web Scraper v1.0", "role": "Google + Amazon scraping"},
                ],
            },
        )


def _count_web_agreements(web_data: dict, attr_code: str) -> dict[str, int]:
    """Count how many web sources found the same attribute."""
    counts: dict[str, int] = {}
    attr_aliases = {
        "weight_kg": ["weight", "wt", "item weight"],
        "colour": ["color", "colour", "clr"],
        "operating_temp_min_c": ["operating_temp", "temp", "temperature"],
        "operating_temp_max_c": ["operating_temp", "temp", "temperature"],
        "certifications": ["certifications", "certs", "certified"],
        "app_name": ["app", "connected app", "smart app"],
        "compatible_valve_types": ["compatible", "valve", "valves"],
        "warranty_months": ["warranty"],
    }
    aliases = attr_aliases.get(attr_code, [attr_code])

    for source_list in [web_data.get("google_results", []), web_data.get("amazon_results", [])]:
        for result in source_list:
            attrs = result.get("attrs", {})
            for key in attrs:
                if any(a in key.lower() for a in aliases):
                    counts[attr_code] = counts.get(attr_code, 0) + 1
    return counts


# Register
from app.pipeline.orchestrator import register_processor
register_processor(4, Stage4Enrich())
