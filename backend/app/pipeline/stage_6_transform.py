"""Stage 6 — Template Transformation.

Maps Iksula normalised values (Layer 1) to client output format (Layer 2).
Uses client_field_mappings and client_value_mappings from DB.
Applies transform rules: direct, unit_convert, lookup, boolean_format, case, duration_format, join, concat, truncate.
"""

import json
import logging
import math
from app.pipeline.base import StageProcessor, StageResult, FieldProvenance
from app.db.client import fetch_one, fetch_all, execute_returning, execute

logger = logging.getLogger(__name__)


class Stage6Transform(StageProcessor):
    stage_number = 6
    stage_name = "Template Transformation"

    def required_models(self) -> list[str]:
        return []  # Rule-based, no AI models needed

    async def process(self, product_id: str, config: dict) -> StageResult:
        product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
        client_id = str(product["client_id"])
        taxonomy_id = str(product["taxonomy_node_id"]) if product["taxonomy_node_id"] else None

        # Get active template for client
        template = await fetch_one(
            "SELECT * FROM retailer_templates WHERE client_id = $1::uuid AND is_active = true ORDER BY last_updated DESC LIMIT 1",
            client_id,
        )
        if not template:
            return StageResult(stage=6, status="failed", metadata={"error": "No active template for client"})

        template_id = str(template["id"])

        # Get all field mappings for this class + template
        mappings = await fetch_all(
            """SELECT cfm.*, ica.attribute_code, ica.attribute_name, ica.data_type, ica.unit as iksula_unit
               FROM client_field_mappings cfm
               JOIN iksula_class_attributes ica ON cfm.iksula_attribute_id = ica.id
               WHERE cfm.template_id = $1::uuid AND cfm.taxonomy_node_id = $2::uuid
               ORDER BY cfm.client_field_order""",
            template_id, taxonomy_id,
        ) if taxonomy_id else []

        # Get all Iksula values for this product
        iksula_values = await fetch_all(
            """SELECT piv.*, ica.attribute_code, ica.data_type, ica.unit
               FROM product_iksula_values piv
               JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
               WHERE piv.product_id = $1::uuid""",
            product_id,
        )
        values_by_attr_id = {str(v["attribute_id"]): v for v in iksula_values}

        # Clear old client values
        await execute(
            "DELETE FROM product_client_values WHERE product_id = $1::uuid AND client_id = $2::uuid",
            product_id, client_id,
        )

        result_fields = []
        mapped_count = 0
        unmapped_count = 0

        for mapping in mappings:
            attr_id = str(mapping["iksula_attribute_id"])
            transform_rule = json.loads(mapping["transform_rule"]) if isinstance(mapping["transform_rule"], str) else mapping["transform_rule"]
            mapping_id = str(mapping["id"])

            iksula_val = values_by_attr_id.get(attr_id)
            if not iksula_val:
                if mapping["mapping_status"] != "unmapped":
                    unmapped_count += 1
                continue

            # Get raw Iksula value
            raw = _get_display_value(iksula_val)
            if raw is None:
                unmapped_count += 1
                continue

            # Apply transform
            client_value = await _apply_transform(
                raw, iksula_val, transform_rule, mapping_id, product_id
            )

            if client_value is not None:
                # Write to Layer 2
                await execute_returning(
                    """INSERT INTO product_client_values
                       (product_id, client_id, template_id, field_mapping_id,
                        client_field_name, client_value,
                        iksula_attribute_id, iksula_raw_value, transform_applied)
                       VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid,
                               $5, $6, $7::uuid, $8, $9)
                       ON CONFLICT (product_id, client_id, field_mapping_id) DO UPDATE SET
                         client_value = EXCLUDED.client_value,
                         iksula_raw_value = EXCLUDED.iksula_raw_value,
                         transform_applied = EXCLUDED.transform_applied,
                         updated_at = now()
                       RETURNING id""",
                    product_id, client_id, template_id, mapping_id,
                    mapping["client_field_name"], str(client_value),
                    attr_id, str(raw),
                    json.dumps(transform_rule),
                )
                mapped_count += 1

                review_status = "auto_approved" if mapping["mapping_status"] in ("auto", "corrected", "manual") else "needs_review"

                result_fields.append(FieldProvenance(
                    field_name=mapping["client_field_name"],
                    value=client_value,
                    source="transformation",
                    model_name=f"{template['template_name']}",
                    confidence=98 if mapping["mapping_status"] in ("auto", "corrected") else 75,
                    review_status=review_status,
                ))
            else:
                unmapped_count += 1

        # Check for unmapped Iksula attributes (attrs with no mapping)
        mapped_attr_ids = {str(m["iksula_attribute_id"]) for m in mappings}
        unmapped_attrs = []
        for v in iksula_values:
            if str(v["attribute_id"]) not in mapped_attr_ids:
                unmapped_attrs.append(v["attribute_code"])
                unmapped_count += 1

        total = mapped_count + unmapped_count
        coverage = round((mapped_count / total) * 100) if total > 0 else 100

        return StageResult(
            stage=6,
            status="needs_review" if unmapped_count > 0 else "complete",
            fields=result_fields,
            metadata={
                "template": template["template_name"],
                "template_version": template["version"],
                "maintained_by": template["maintained_by"],
                "mapped": mapped_count,
                "unmapped": unmapped_count,
                "coverage_pct": coverage,
                "unmapped_attrs": unmapped_attrs,
                "export_formats": template["export_formats"],
                "transform_summary": [
                    {
                        "iksula_field": m["attribute_code"],
                        "client_field": m["client_field_name"],
                        "transform": json.loads(m["transform_rule"]) if isinstance(m["transform_rule"], str) else m["transform_rule"],
                        "status": m["mapping_status"],
                    }
                    for m in mappings
                ],
            },
        )


def _get_display_value(row: dict):
    """Get the value from an Iksula value row."""
    if row["value_text"] is not None:
        return row["value_text"]
    if row["value_numeric"] is not None:
        return float(row["value_numeric"])
    if row["value_boolean"] is not None:
        return row["value_boolean"]
    if row["value_array"]:
        return list(row["value_array"])
    return None


async def _apply_transform(raw, iksula_row: dict, rule: dict, mapping_id: str, product_id: str):
    """Apply a transform rule to convert Iksula value → client value."""
    transform_type = rule.get("type", "direct")

    if transform_type == "direct":
        return raw

    elif transform_type == "unit_convert":
        if isinstance(raw, (int, float)):
            factor = rule.get("factor", 1)
            return round(raw * factor, 2)
        return raw

    elif transform_type == "lookup":
        # Look up client_value_mappings
        if isinstance(raw, str):
            row = await fetch_one(
                """SELECT client_value FROM client_value_mappings
                   WHERE client_field_mapping_id = $1::uuid AND iksula_value_code = $2""",
                mapping_id, raw,
            )
            return row["client_value"] if row else raw
        return raw

    elif transform_type == "boolean_format":
        true_val = rule.get("true", "Yes")
        false_val = rule.get("false", "No")
        if isinstance(raw, bool):
            return true_val if raw else false_val
        return true_val if str(raw).lower() in ("true", "yes", "1") else false_val

    elif transform_type == "case":
        style = rule.get("style", "title")
        if isinstance(raw, str):
            if style == "title":
                return raw.title()
            elif style == "upper":
                return raw.upper()
            elif style == "lower":
                return raw.lower()
        return raw

    elif transform_type == "duration_format":
        output = rule.get("output", "years")
        if isinstance(raw, (int, float)):
            months = int(raw)
            if output == "years":
                years = months / 12
                if years == int(years):
                    return f"{int(years)} Year{'s' if years != 1 else ''}"
                return f"{months} Months"
        return raw

    elif transform_type == "join":
        separator = rule.get("separator", ", ")
        use_labels = rule.get("use_labels", False)
        if isinstance(raw, list):
            if use_labels:
                # Look up labels from allowed values
                labels = []
                for code in raw:
                    row = await fetch_one(
                        "SELECT value_label FROM iksula_allowed_values WHERE value_code = $1 LIMIT 1", code,
                    )
                    labels.append(row["value_label"] if row else code)
                return separator.join(labels)
            return separator.join(str(v) for v in raw)
        return str(raw)

    elif transform_type == "truncate":
        max_len = rule.get("max_length", 80)
        s = str(raw)
        return s[:max_len] if len(s) > max_len else s

    else:
        logger.warning(f"Unknown transform type: {transform_type}")
        return raw


# Register
from app.pipeline.orchestrator import register_processor
register_processor(6, Stage6Transform())
