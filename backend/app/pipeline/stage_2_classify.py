"""Stage 2 — Categorisation.

Assigns product to taxonomy: Department → Category → Class → Subclass.
Loads mandatory attributes for the assigned class.
"""

import json
import logging
from app.pipeline.base import StageProcessor, StageResult, FieldProvenance
from app.ai.router import invoke_model
from app.db.client import fetch_one, fetch_all, execute

logger = logging.getLogger(__name__)

DEFAULT_AUTO_APPROVE = 85
DEFAULT_NEEDS_REVIEW = 60
DEFAULT_HIL_BELOW = 80


class Stage2Classify(StageProcessor):
    stage_number = 2
    stage_name = "Categorisation"

    def required_models(self) -> list[str]:
        return ["taxonomy_classification"]

    async def process(self, product_id: str, config: dict) -> StageResult:
        auto_threshold = config.get("confidence", {}).get("auto_approve_threshold", DEFAULT_AUTO_APPROVE)
        hil_below = config.get("confidence", {}).get("require_human_confirm_below", DEFAULT_HIL_BELOW)

        # Gather product data for classification
        product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
        known_rows = await fetch_all(
            """SELECT ica.attribute_code, piv.value_text, piv.value_numeric
               FROM product_iksula_values piv
               JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
               WHERE piv.product_id = $1::uuid""",
            product_id,
        )
        known_attributes = {}
        for r in known_rows:
            known_attributes[r["attribute_code"]] = r["value_text"] or (str(r["value_numeric"]) if r["value_numeric"] is not None else None)

        result = await invoke_model("classify", {
            "product_id": product_id,
            "product_name": product["product_name"] or "",
            "model_number": product["model_number"] or "",
            "known_attributes": known_attributes,
        })
        classification = result.value  # {department, category, class, subclass}
        if not isinstance(classification, dict) or "subclass" not in classification:
            logger.warning(f"Classification returned unexpected format: {classification}")
            return StageResult(stage=2, status="failed", metadata={"error": "Classification failed"})

        fields = []
        lowest_confidence = 100

        # Find the matching taxonomy node (subclass level)
        subclass_code = classification["subclass"].get("code", "")
        taxonomy_node = await fetch_one(
            "SELECT id FROM taxonomy_nodes WHERE code = $1", subclass_code,
        )

        if taxonomy_node:
            # Assign taxonomy to product
            await execute(
                "UPDATE products SET taxonomy_node_id = $1::uuid, updated_at = now() WHERE id = $2::uuid",
                str(taxonomy_node["id"]), product_id,
            )

        # Record classification results as provenance
        for level in ["department", "category", "class", "subclass"]:
            data = classification[level]
            confidence = data["confidence"]
            lowest_confidence = min(lowest_confidence, confidence)

            review_status = "auto_approved" if confidence >= auto_threshold else "needs_review"

            fields.append(FieldProvenance(
                field_name=f"taxonomy_{level}",
                value=data["name"],
                source="classification",
                model_name=result.model_name,
                confidence=confidence,
                review_status=review_status,
            ))

        # Get mandatory attributes for assigned class
        mandatory_attrs = []
        if taxonomy_node:
            attrs = await fetch_all(
                """SELECT ica.attribute_code, ica.attribute_name, ica.is_mandatory
                   FROM iksula_class_attributes ica
                   WHERE ica.taxonomy_node_id = $1::uuid
                   ORDER BY ica.display_order""",
                str(taxonomy_node["id"]),
            )

            # Check which mandatory attrs already have values from Stage 1
            for attr in attrs:
                if not attr["is_mandatory"]:
                    continue
                existing = await fetch_one(
                    """SELECT id FROM product_iksula_values
                       WHERE product_id = $1::uuid AND attribute_id = (
                         SELECT id FROM iksula_class_attributes WHERE attribute_code = $2
                       )""",
                    product_id, attr["attribute_code"],
                )
                mandatory_attrs.append({
                    "code": attr["attribute_code"],
                    "name": attr["attribute_name"],
                    "found": existing is not None,
                })

        # Determine if HIL needed
        needs_hil = lowest_confidence < hil_below
        overall_status = "needs_review" if needs_hil else "complete"

        # Build alternatives from classification result
        path = " > ".join([classification.get(l, {}).get("name", "?") for l in ["department", "category", "class", "subclass"]])
        alternatives = [{"path": path, "confidence": lowest_confidence}]

        found_count = sum(1 for a in mandatory_attrs if a["found"])
        total_mandatory = len(mandatory_attrs)

        return StageResult(
            stage=2,
            status=overall_status,
            fields=fields,
            metadata={
                "model": result.model_name,
                "taxonomy_path": classification["subclass"].get("code", ""),
                "overall_confidence": lowest_confidence,
                "mandatory_attrs": mandatory_attrs,
                "mandatory_found": found_count,
                "mandatory_total": total_mandatory,
                "alternatives": alternatives,
                "taxonomy_version": "Iksula Retail Taxonomy v4.2 — SiteOne edition",
                "total_classes": 847,
            },
        )


# Register
from app.pipeline.orchestrator import register_processor
register_processor(2, Stage2Classify())
