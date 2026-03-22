"""Stage 7 — Final Review + Publish.

Aggregates all unresolved items from previous stages.
Calculates overall readiness score.
Handles publish action → writes final record, pushes to PIM.
"""

import json
import logging
from app.pipeline.base import StageProcessor, StageResult, FieldProvenance
from app.db.client import fetch_one, fetch_all, execute

logger = logging.getLogger(__name__)


class Stage7Review(StageProcessor):
    stage_number = 7
    stage_name = "Final Review + Publish"

    def required_models(self) -> list[str]:
        return []

    async def process(self, product_id: str, config: dict) -> StageResult:
        product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)

        # Gather ALL fields across all stages with their current status
        all_values = await fetch_all(
            """SELECT piv.*, ica.attribute_code, ica.attribute_name, ica.is_mandatory, ica.display_order
               FROM product_iksula_values piv
               JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
               WHERE piv.product_id = $1::uuid
               ORDER BY ica.display_order""",
            product_id,
        )

        # Count by status
        auto_approved = 0
        human_approved = 0
        human_edited = 0
        needs_review = 0
        low_confidence = 0
        rejected = 0

        review_items = []
        for v in all_values:
            status = v["review_status"]
            if status == "auto_approved":
                auto_approved += 1
            elif status == "human_approved":
                human_approved += 1
            elif status == "human_edited":
                human_edited += 1
            elif status == "needs_review":
                needs_review += 1
                review_items.append(v)
            elif status == "low_confidence":
                low_confidence += 1
                review_items.append(v)
            elif status == "rejected":
                rejected += 1

        total = len(all_values)
        approved_total = auto_approved + human_approved + human_edited
        overall_score = round((approved_total / total) * 100) if total > 0 else 0

        # Update product score
        await execute(
            "UPDATE products SET overall_confidence = $1, updated_at = now() WHERE id = $2::uuid",
            float(overall_score), product_id,
        )

        # Get audit trail for this product
        audit = await fetch_all(
            """SELECT * FROM audit_trail
               WHERE product_id = $1::uuid
               ORDER BY created_at DESC LIMIT 50""",
            product_id,
        )

        # Get client values (Layer 2) for export preview
        client_values = await fetch_all(
            """SELECT client_field_name, client_value, iksula_raw_value, transform_applied, review_status
               FROM product_client_values
               WHERE product_id = $1::uuid
               ORDER BY (SELECT client_field_order FROM client_field_mappings WHERE id = field_mapping_id)""",
            product_id,
        )

        # Build review queue items
        fields = []
        for v in review_items:
            value = v["value_text"] or (str(v["value_numeric"]) if v["value_numeric"] is not None else None) or (str(v["value_boolean"]) if v["value_boolean"] is not None else None)
            fields.append(FieldProvenance(
                field_name=v["attribute_code"],
                value=value,
                source=v["source"],
                model_name=v["model_name"],
                confidence=v["confidence"] or 0,
                review_status=v["review_status"],
            ))

        can_publish = needs_review == 0 and low_confidence == 0

        return StageResult(
            stage=7,
            status="complete" if can_publish else "needs_review",
            fields=fields,
            metadata={
                "summary": {
                    "total_fields": total,
                    "auto_approved": auto_approved,
                    "human_approved": human_approved,
                    "human_edited": human_edited,
                    "needs_review": needs_review,
                    "low_confidence": low_confidence,
                    "rejected": rejected,
                    "overall_score": overall_score,
                },
                "can_publish": can_publish,
                "product_title": product["product_title"],
                "short_description": product["short_description"],
                "long_description": product["long_description"],
                "client_values": [dict(cv) for cv in client_values],
                "audit_trail": [
                    {
                        "action": a["action"],
                        "field": a["field_name"],
                        "layer": a["layer"],
                        "old_value": a["old_value"],
                        "new_value": a["new_value"],
                        "actor": a["actor_id"],
                        "model": a["model_name"],
                        "reason": a["reason"],
                        "timestamp": str(a["created_at"]),
                    }
                    for a in audit
                ],
            },
        )


# Register
from app.pipeline.orchestrator import register_processor
register_processor(7, Stage7Review())
