"""AI-based DIM anomaly detection.

Compares a product's dimensions/weight/values against existing products
in the same class. Flags statistical outliers and uses LLM for
contextual validation.

Two methods:
1. Statistical — compute class averages/stddev from DB, flag if > 2 std devs away
2. LLM-based — ask GPT-4o "does this make sense for this product type?"
"""

from __future__ import annotations


import json
import logging
import math
from app.db.client import fetch_all, fetch_one
from app.ai.router import invoke_model
from app.config import settings

logger = logging.getLogger(__name__)

# Attributes to check for anomalies
NUMERIC_CHECK_ATTRS = [
    "weight_kg", "shipping_weight_kg",
    "width_cm", "depth_cm", "height_cm",
    "operating_temp_min_c", "operating_temp_max_c",
    "warranty_months",
]

STDDEV_THRESHOLD = 2.0  # Flag if > 2 standard deviations from class mean


async def detect_anomalies(product_id: str, taxonomy_node_id: str) -> list[dict]:
    """Run anomaly detection on a product's numeric values.

    Returns list of anomaly findings:
    [{"field": "weight_kg", "value": 15.0, "class_avg": 0.8, "class_stddev": 0.3,
      "severity": "high", "message": "Weight 15kg is 47x the class average (0.8kg)",
      "ai_assessment": "This weight seems incorrect for a smart irrigation controller..."}]
    """
    anomalies = []

    # Get product's current values
    product_values = await fetch_all(
        """SELECT piv.value_numeric, ica.attribute_code, ica.attribute_name, ica.unit
           FROM product_iksula_values piv
           JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
           WHERE piv.product_id = $1::uuid AND piv.value_numeric IS NOT NULL""",
        product_id,
    )

    if not product_values:
        return []

    # ── Method 1: Statistical anomaly detection ──
    # Get class statistics from published products in the same taxonomy class
    for pv in product_values:
        attr_code = pv["attribute_code"]
        if attr_code not in NUMERIC_CHECK_ATTRS:
            continue

        current_value = float(pv["value_numeric"])

        # Compute class avg and stddev from existing published products
        stats = await fetch_one(
            """SELECT
                 AVG(piv.value_numeric) as avg_val,
                 STDDEV(piv.value_numeric) as stddev_val,
                 MIN(piv.value_numeric) as min_val,
                 MAX(piv.value_numeric) as max_val,
                 COUNT(*) as sample_count
               FROM product_iksula_values piv
               JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
               JOIN products p ON piv.product_id = p.id
               WHERE ica.attribute_code = $1
                 AND p.taxonomy_node_id = $2::uuid
                 AND p.status = 'published'
                 AND p.id != $3::uuid
                 AND piv.value_numeric IS NOT NULL""",
            attr_code, taxonomy_node_id, product_id,
        )

        if not stats or not stats["avg_val"] or stats["sample_count"] < 3:
            continue  # Not enough data for meaningful comparison

        avg = float(stats["avg_val"])
        stddev = float(stats["stddev_val"]) if stats["stddev_val"] else 0
        min_val = float(stats["min_val"])
        max_val = float(stats["max_val"])
        count = stats["sample_count"]

        if stddev == 0:
            stddev = avg * 0.1  # Default 10% if all values are the same

        # Check if current value is an outlier
        if stddev > 0:
            z_score = abs(current_value - avg) / stddev
        else:
            z_score = 0

        if z_score > STDDEV_THRESHOLD:
            ratio = current_value / avg if avg > 0 else float('inf')

            severity = "high" if z_score > 4 else "medium" if z_score > 3 else "low"

            anomaly = {
                "field": attr_code,
                "field_name": pv["attribute_name"],
                "unit": pv["unit"],
                "value": current_value,
                "class_avg": round(avg, 2),
                "class_stddev": round(stddev, 2),
                "class_min": round(min_val, 2),
                "class_max": round(max_val, 2),
                "class_sample_count": count,
                "z_score": round(z_score, 1),
                "ratio_to_avg": round(ratio, 1),
                "severity": severity,
                "method": "statistical",
                "message": (
                    f"{pv['attribute_name']} = {current_value} {pv['unit'] or ''} is "
                    f"{'%.1f' % ratio}x the class average ({avg:.2f} {pv['unit'] or ''}). "
                    f"Class range: {min_val:.2f} – {max_val:.2f} across {count} products."
                ),
            }
            anomalies.append(anomaly)

    # ── Method 2: LLM contextual validation ──
    # Ask AI if the values make sense for this product type
    if anomalies or not settings.demo_mode:
        ai_assessment = await _get_ai_assessment(product_id, product_values, anomalies, taxonomy_node_id)
        if ai_assessment:
            for anomaly in anomalies:
                field_assessment = ai_assessment.get(anomaly["field"])
                if field_assessment:
                    anomaly["ai_assessment"] = field_assessment.get("assessment", "")
                    anomaly["ai_suggestion"] = field_assessment.get("suggestion", "")
                    # AI can upgrade/downgrade severity
                    if field_assessment.get("likely_correct"):
                        anomaly["severity"] = "info"
                        anomaly["ai_override"] = "AI believes this value is correct despite being unusual"

            # AI may flag additional issues not caught by statistics
            for field_code, assessment in ai_assessment.items():
                if not assessment.get("flagged"):
                    continue
                if any(a["field"] == field_code for a in anomalies):
                    continue  # Already flagged
                anomalies.append({
                    "field": field_code,
                    "field_name": assessment.get("field_name", field_code),
                    "value": assessment.get("value"),
                    "severity": assessment.get("severity", "low"),
                    "method": "ai",
                    "message": assessment.get("assessment", ""),
                    "ai_assessment": assessment.get("assessment", ""),
                    "ai_suggestion": assessment.get("suggestion", ""),
                })

    return anomalies


async def _get_ai_assessment(
    product_id: str,
    product_values: list,
    statistical_anomalies: list,
    taxonomy_node_id: str,
) -> dict | None:
    """Ask LLM to validate product dimensions contextually."""
    product = await fetch_one("SELECT product_name, model_number FROM products WHERE id = $1::uuid", product_id)
    taxonomy = await fetch_one("SELECT name, full_path FROM taxonomy_nodes WHERE id = $1::uuid", taxonomy_node_id)

    values_summary = {pv["attribute_code"]: f"{pv['value_numeric']} {pv['unit'] or ''}" for pv in product_values}
    flagged_summary = [{"field": a["field"], "value": a["value"], "class_avg": a.get("class_avg"), "message": a["message"]} for a in statistical_anomalies]

    prompt = f"""You are a product data quality expert. Review these product dimensions and values for plausibility.

Product: {product['product_name'] if product else 'Unknown'}
Model: {product['model_number'] if product else 'Unknown'}
Category: {taxonomy['full_path'] if taxonomy else 'Unknown'}

Current values:
{json.dumps(values_summary, indent=2)}

Statistical anomalies flagged:
{json.dumps(flagged_summary, indent=2) if flagged_summary else 'None'}

For EACH value, assess:
1. Does this value make physical sense for this type of product?
2. If flagged as statistical outlier, is the value likely correct (just unusual) or likely an error?
3. Are there any other values that seem wrong even if not statistically flagged?

Return JSON where keys are attribute_codes:
{{
  "weight_kg": {{
    "flagged": true/false,
    "likely_correct": true/false,
    "severity": "high/medium/low/info",
    "field_name": "Weight",
    "value": 0.36,
    "assessment": "0.36 kg is reasonable for a small electronic controller",
    "suggestion": "No action needed"
  }}
}}

Only include fields that need attention or that were flagged."""

    try:
        result = await invoke_model("validate_dims", data={"product_id": product_id}, prompt=prompt)
        if isinstance(result.value, dict):
            return result.value
    except Exception as e:
        logger.warning(f"AI DIM assessment failed: {e}")

    return None
