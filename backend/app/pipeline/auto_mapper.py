"""AI-powered auto-mapping for client templates.

When a new client template is uploaded:
1. Extract the client's field names from the template
2. Load Iksula normalised attributes for the taxonomy class
3. Use GPT-4o to match client fields → Iksula attributes
4. Generate transform rules for each mapping
5. Save mappings to client_field_mappings with status='auto'
6. Human reviews and corrects via HIL

Also handles value mapping:
- For enum fields, AI maps client values to Iksula picklist values
"""

import json
import logging
from app.ai.router import invoke_model
from app.db.client import fetch_all, fetch_one, execute_returning

logger = logging.getLogger(__name__)


async def auto_map_template(
    client_id: str,
    template_id: str,
    taxonomy_node_id: str,
    client_fields: list[dict],  # [{"name": "Product Color", "code": "color", "sample_values": ["Gray","White"]}]
) -> dict:
    """AI auto-maps client template fields to Iksula normalised attributes.

    Args:
        client_id: The client (retailer) ID
        template_id: The retailer template ID
        taxonomy_node_id: The taxonomy class to map for
        client_fields: List of client field definitions extracted from uploaded template

    Returns:
        {"mapped": 15, "unmapped": 2, "confidence_avg": 87, "mappings": [...]}
    """
    # Load Iksula attributes for this class
    iksula_attrs = await fetch_all(
        """SELECT id, attribute_code, attribute_name, data_type, unit, is_mandatory
           FROM iksula_class_attributes
           WHERE taxonomy_node_id = $1::uuid
           ORDER BY display_order""",
        taxonomy_node_id,
    )

    if not iksula_attrs:
        return {"mapped": 0, "unmapped": len(client_fields), "error": "No Iksula attributes for this class"}

    # Load existing allowed values for enum fields
    picklist_info = {}
    for attr in iksula_attrs:
        if attr["data_type"] in ("enum", "multi_enum"):
            values = await fetch_all(
                "SELECT value_code, value_label FROM iksula_allowed_values WHERE attribute_id = $1::uuid",
                str(attr["id"]),
            )
            picklist_info[attr["attribute_code"]] = [{"code": v["value_code"], "label": v["value_label"]} for v in values]

    # Build prompt for AI
    iksula_summary = []
    for attr in iksula_attrs:
        entry = f"- {attr['attribute_code']} ({attr['attribute_name']}): type={attr['data_type']}, unit={attr['unit'] or 'none'}, mandatory={attr['is_mandatory']}"
        if attr["attribute_code"] in picklist_info:
            values = picklist_info[attr["attribute_code"]]
            entry += f", allowed_values=[{', '.join(v['label'] for v in values)}]"
        iksula_summary.append(entry)

    client_summary = []
    for cf in client_fields:
        entry = f"- {cf['name']} (code: {cf.get('code', 'unknown')})"
        if cf.get("sample_values"):
            entry += f", sample_values: {cf['sample_values'][:5]}"
        client_summary.append(entry)

    prompt = f"""You are a product data mapping specialist. Map client (retailer) template fields to Iksula normalised attributes.

IKSULA NORMALISED ATTRIBUTES:
{chr(10).join(iksula_summary)}

CLIENT TEMPLATE FIELDS:
{chr(10).join(client_summary)}

For each client field, find the best matching Iksula attribute. Consider:
- Semantic meaning (not just name similarity)
- Data type compatibility
- Unit compatibility (client may use different units)

Return JSON array of mappings:
[
  {{
    "client_field_name": "Product Color",
    "client_field_code": "color",
    "iksula_attribute_code": "colour",
    "confidence": 95,
    "transform_rule": {{"type": "lookup"}},
    "reasoning": "Both refer to product colour, client uses 'Color' spelling"
  }},
  {{
    "client_field_name": "Weight (lbs)",
    "client_field_code": "weight_lbs",
    "iksula_attribute_code": "weight_kg",
    "confidence": 90,
    "transform_rule": {{"type": "unit_convert", "from": "kg", "to": "lbs", "factor": 2.20462}},
    "reasoning": "Same attribute, different units — Iksula stores kg, client wants lbs"
  }},
  {{
    "client_field_name": "Custom Field XYZ",
    "client_field_code": "custom_xyz",
    "iksula_attribute_code": null,
    "confidence": 0,
    "transform_rule": null,
    "reasoning": "No matching Iksula attribute found"
  }}
]

Rules:
- Set iksula_attribute_code to null if no match found
- Set confidence 0-100 based on match quality
- Choose appropriate transform_rule type: direct, unit_convert, lookup, boolean_format, case, duration_format, join
- For enum fields where client uses different values, use "lookup" transform"""

    result = await invoke_model("map_template", prompt=prompt)
    ai_mappings = result.value if isinstance(result.value, list) else []

    # Save mappings to DB
    saved = 0
    unmapped = 0
    total_confidence = 0

    for mapping in ai_mappings:
        iksula_code = mapping.get("iksula_attribute_code")

        if not iksula_code:
            unmapped += 1
            continue

        # Find the Iksula attribute ID
        iksula_attr = next((a for a in iksula_attrs if a["attribute_code"] == iksula_code), None)
        if not iksula_attr:
            unmapped += 1
            continue

        confidence = mapping.get("confidence", 50)
        total_confidence += confidence
        transform_rule = mapping.get("transform_rule", {"type": "direct"})
        mapping_status = "auto" if confidence >= 80 else "unmapped"

        # Insert into client_field_mappings
        await execute_returning(
            """INSERT INTO client_field_mappings
               (client_id, template_id, taxonomy_node_id, iksula_attribute_id,
                client_field_name, client_field_code, client_field_order,
                is_mandatory, transform_rule, mapping_status, auto_map_confidence)
               VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid,
                       $5, $6, $7, $8, $9::jsonb, $10, $11)
               ON CONFLICT (template_id, taxonomy_node_id, iksula_attribute_id)
               DO UPDATE SET
                 client_field_name = EXCLUDED.client_field_name,
                 client_field_code = EXCLUDED.client_field_code,
                 transform_rule = EXCLUDED.transform_rule,
                 mapping_status = EXCLUDED.mapping_status,
                 updated_at = now()
               RETURNING id""",
            client_id, template_id, taxonomy_node_id, str(iksula_attr["id"]),
            mapping["client_field_name"], mapping.get("client_field_code", ""),
            saved,  # order
            iksula_attr["is_mandatory"],
            json.dumps(transform_rule),
            mapping_status,
            confidence,
        )
        saved += 1

        # Auto-map values for enum fields if transform is "lookup"
        if transform_rule.get("type") == "lookup" and iksula_code in picklist_info:
            await _auto_map_values(
                client_id, template_id, taxonomy_node_id,
                str(iksula_attr["id"]), iksula_code,
                mapping.get("client_field_code", ""),
                picklist_info[iksula_code],
                mapping.get("sample_values", []),
            )

    avg_confidence = round(total_confidence / saved) if saved > 0 else 0

    return {
        "mapped": saved,
        "unmapped": unmapped,
        "confidence_avg": avg_confidence,
        "mappings": ai_mappings,
        "model": result.model_name,
    }


async def _auto_map_values(
    client_id: str, template_id: str, taxonomy_node_id: str,
    iksula_attr_id: str, iksula_attr_code: str,
    client_field_code: str, iksula_values: list[dict],
    client_sample_values: list[str],
):
    """AI-map enum values: Iksula picklist → client values."""
    if not client_sample_values:
        return

    # Get the mapping ID
    mapping = await fetch_one(
        """SELECT id FROM client_field_mappings
           WHERE template_id = $1::uuid AND taxonomy_node_id = $2::uuid AND iksula_attribute_id = $3::uuid""",
        template_id, taxonomy_node_id, iksula_attr_id,
    )
    if not mapping:
        return

    mapping_id = str(mapping["id"])

    # For each Iksula picklist value, try to find the client equivalent
    for iv in iksula_values:
        # Simple match: check if any client sample value matches (case-insensitive)
        matched_client = None
        for csv in client_sample_values:
            if csv.lower() == iv["label"].lower() or csv.lower() == iv["code"].lower():
                matched_client = csv
                break

        if matched_client:
            await execute_returning(
                """INSERT INTO client_value_mappings
                   (client_field_mapping_id, iksula_value_code, iksula_value_label, client_value, mapping_status)
                   VALUES ($1::uuid, $2, $3, $4, 'auto')
                   ON CONFLICT (client_field_mapping_id, iksula_value_code) DO NOTHING
                   RETURNING id""",
                mapping_id, iv["code"], iv["label"], matched_client,
            )
