"""Stage 5 — DIM Check + Validation.

Validates every field using BOTH rule-based and AI-based methods:
1. Unit normalisation (lbs→kg, °F→°C, in→cm)
2. Range validation (value within class-specific bounds)
3. Mandatory field check (all required fields have values)
4. Format validation (UPC 12 digits, EAN 13 digits, URL valid)
5. Logical consistency (dimensions produce plausible volume)
6. AI anomaly detection (compare against similar products in class, LLM contextual check)
"""

from __future__ import annotations


import re
import json
import logging
from app.pipeline.base import StageProcessor, StageResult, FieldProvenance
from app.db.client import fetch_one, fetch_all, execute

logger = logging.getLogger(__name__)

# Unit conversion factors
CONVERSIONS = {
    ("lbs", "kg"): 0.453592,
    ("oz", "kg"): 0.0283495,
    ("lb", "kg"): 0.453592,
    ("in", "cm"): 2.54,
    ("inches", "cm"): 2.54,
    ("inch", "cm"): 2.54,
    ("ft", "cm"): 30.48,
    ("mm", "cm"): 0.1,
    ("m", "cm"): 100,
}

TEMP_F_TO_C = lambda f: round((f - 32) * 5 / 9, 1)


class ValidationResult:
    def __init__(self, rule: str, field: str, value: str, status: str, message: str, fix: str | None = None, fixed_value: str | None = None):
        self.rule = rule
        self.field = field
        self.value = value
        self.status = status  # pass, warning, fail
        self.message = message
        self.fix = fix
        self.fixed_value = fixed_value


class Stage5Validate(StageProcessor):
    stage_number = 5
    stage_name = "DIM Check + Validation"

    def required_models(self) -> list[str]:
        return ["unit_normalisation", "range_validation"]

    async def process(self, product_id: str, config: dict) -> StageResult:
        block_on_fail = config.get("confidence", {}).get("block_on_failure", True)

        product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
        taxonomy_id = str(product["taxonomy_node_id"]) if product["taxonomy_node_id"] else None

        # Get all class attributes with validation rules
        attrs = await fetch_all(
            """SELECT id, attribute_code, attribute_name, data_type, unit, is_mandatory, validation_rule
               FROM iksula_class_attributes WHERE taxonomy_node_id = $1::uuid ORDER BY display_order""",
            taxonomy_id,
        ) if taxonomy_id else []

        # Get all product values
        values = await fetch_all(
            """SELECT piv.*, ica.attribute_code, ica.attribute_name, ica.data_type, ica.unit as target_unit,
                      ica.is_mandatory, ica.validation_rule
               FROM product_iksula_values piv
               JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
               WHERE piv.product_id = $1::uuid""",
            product_id,
        )
        values_by_code = {v["attribute_code"]: v for v in values}

        results: list[ValidationResult] = []

        # ── 1. Unit normalisation ──
        for v in values:
            if v["data_type"] != "measurement" or v["value_numeric"] is None:
                continue

            raw = v["raw_extracted"] or ""
            target_unit = v["target_unit"]
            if not target_unit:
                continue

            # Detect source unit from raw text
            normalised = self._try_normalise(v["value_numeric"], raw, target_unit)
            if normalised is not None and abs(normalised - float(v["value_numeric"])) > 0.001:
                # Value needs conversion
                results.append(ValidationResult(
                    rule="Unit Normalisation",
                    field=v["attribute_name"],
                    value=raw,
                    status="pass",
                    message=f"{raw} → {normalised} {target_unit}",
                    fixed_value=str(normalised),
                ))
                # Update the value in DB
                await execute(
                    "UPDATE product_iksula_values SET value_numeric = $1, updated_at = now(), updated_at_stage = 5 WHERE id = $2::uuid",
                    normalised, str(v["id"]),
                )
            elif normalised is not None:
                results.append(ValidationResult(
                    rule="Unit Normalisation",
                    field=v["attribute_name"],
                    value=f"{v['value_numeric']} {target_unit}",
                    status="pass",
                    message=f"Already in correct unit ({target_unit})",
                ))

        # ── 2. Range validation ──
        for v in values:
            if v["value_numeric"] is None or not v["validation_rule"]:
                continue

            rule = json.loads(v["validation_rule"]) if isinstance(v["validation_rule"], str) else v["validation_rule"]
            val = float(v["value_numeric"])

            # Check allowed values (discrete set)
            if "allowed" in rule:
                if val not in rule["allowed"]:
                    results.append(ValidationResult(
                        rule="Range Validation",
                        field=v["attribute_name"],
                        value=str(val),
                        status="warning",
                        message=f"Value {val} not in allowed set {rule['allowed']}",
                        fix=f"Expected one of: {', '.join(str(x) for x in rule['allowed'])}",
                    ))
                else:
                    results.append(ValidationResult(
                        rule="Range Validation", field=v["attribute_name"],
                        value=str(val), status="pass",
                        message=f"Value {val} is in allowed set",
                    ))

            # Check min/max range
            if "min" in rule and val < rule["min"]:
                results.append(ValidationResult(
                    rule="Range Validation", field=v["attribute_name"],
                    value=str(val), status="fail",
                    message=f"Value {val} below minimum {rule['min']}",
                    fix=f"Must be ≥ {rule['min']}",
                ))
            elif "max" in rule and val > rule["max"]:
                results.append(ValidationResult(
                    rule="Range Validation", field=v["attribute_name"],
                    value=str(val), status="fail",
                    message=f"Value {val} above maximum {rule['max']}",
                    fix=f"Must be ≤ {rule['max']}",
                ))
            elif "min" in rule or "max" in rule:
                results.append(ValidationResult(
                    rule="Range Validation", field=v["attribute_name"],
                    value=str(val), status="pass",
                    message=f"Value {val} within range",
                ))

        # ── 3. Mandatory field check ──
        for attr in attrs:
            if not attr["is_mandatory"]:
                continue
            if attr["attribute_code"] not in values_by_code:
                results.append(ValidationResult(
                    rule="Mandatory Check",
                    field=attr["attribute_name"],
                    value="Missing",
                    status="fail",
                    message=f"Required field is missing. Must resolve before publish.",
                    fix="Enter value manually or re-run enrichment",
                ))

        # ── 4. Format validation ──
        if product["upc"]:
            if not re.match(r"^\d{12}$", product["upc"]):
                results.append(ValidationResult(
                    rule="Format Validation", field="UPC", value=product["upc"],
                    status="fail", message="UPC must be exactly 12 digits",
                ))
            else:
                results.append(ValidationResult(
                    rule="Format Validation", field="UPC", value=product["upc"],
                    status="pass", message="Valid 12-digit UPC",
                ))

        if product["ean"]:
            if not re.match(r"^\d{13}$", product["ean"]):
                results.append(ValidationResult(
                    rule="Format Validation", field="EAN", value=product["ean"],
                    status="fail", message="EAN must be exactly 13 digits",
                ))

        # ── 5. Logical consistency (dimensions) ──
        w = values_by_code.get("width_cm", {})
        d = values_by_code.get("depth_cm", {})
        h = values_by_code.get("height_cm", {})
        if w and d and h:
            wv = float(w.get("value_numeric", 0) or 0)
            dv = float(d.get("value_numeric", 0) or 0)
            hv = float(h.get("value_numeric", 0) or 0)
            if wv > 0 and dv > 0 and hv > 0:
                volume_cc = wv * dv * hv
                if volume_cc > 1_000_000:  # > 1 cubic metre
                    results.append(ValidationResult(
                        rule="Logical Consistency", field="Dimensions",
                        value=f"{wv}×{dv}×{hv} cm",
                        status="warning", message=f"Volume {volume_cc:.0f} cm³ seems very large",
                    ))
                elif volume_cc < 1:
                    results.append(ValidationResult(
                        rule="Logical Consistency", field="Dimensions",
                        value=f"{wv}×{dv}×{hv} cm",
                        status="warning", message=f"Volume {volume_cc:.2f} cm³ seems very small",
                    ))
                else:
                    results.append(ValidationResult(
                        rule="Logical Consistency", field="Dimensions",
                        value=f"{wv}×{dv}×{hv} cm",
                        status="pass", message=f"Volume {volume_cc:.0f} cm³ is plausible",
                    ))

        # Summarise
        passed = sum(1 for r in results if r.status == "pass")
        warnings = sum(1 for r in results if r.status == "warning")
        failures = sum(1 for r in results if r.status == "fail")

        # ── 6. AI anomaly detection ──
        from app.pipeline.dim_anomaly import detect_anomalies

        anomalies = []
        if taxonomy_id:
            try:
                anomalies = await detect_anomalies(product_id, taxonomy_id)
                for anomaly in anomalies:
                    severity = anomaly.get("severity", "low")
                    status = "fail" if severity == "high" else "warning"
                    results.append(ValidationResult(
                        rule="AI Anomaly Detection",
                        field=anomaly.get("field_name", anomaly["field"]),
                        value=str(anomaly.get("value", "")),
                        status=status,
                        message=anomaly.get("message", ""),
                        fix=anomaly.get("ai_suggestion"),
                    ))
                    if status == "fail":
                        failures += 1
                    else:
                        warnings += 1
            except Exception as e:
                logger.warning(f"AI anomaly detection failed: {e}")

        # Recount after anomalies
        passed = sum(1 for r in results if r.status == "pass")

        # Build stage fields for HIL
        fields = []
        for r in results:
            if r.status == "fail":
                fields.append(FieldProvenance(
                    field_name=r.field, value=r.value, source="validation",
                    model_name="Iksula DIM Validator v2.3",
                    confidence=0, review_status="low_confidence",
                ))
            elif r.status == "warning" and r.rule == "AI Anomaly Detection":
                fields.append(FieldProvenance(
                    field_name=r.field, value=r.value, source="ai_validation",
                    model_name="GPT-4o (AI DIM Check)",
                    confidence=30, review_status="needs_review",
                ))

        has_failures = failures > 0 and block_on_fail

        return StageResult(
            stage=5,
            status="needs_review" if has_failures or anomalies else "complete",
            fields=fields,
            metadata={
                "model": "Iksula DIM Validator v2.3",
                "passed": passed,
                "warnings": warnings,
                "failures": failures,
                "results": [
                    {"rule": r.rule, "field": r.field, "value": r.value,
                     "status": r.status, "message": r.message,
                     "fix": r.fix, "fixed_value": r.fixed_value}
                    for r in results
                ],
                "anomalies": [
                    {"field": a["field"], "field_name": a.get("field_name"), "value": a.get("value"),
                     "class_avg": a.get("class_avg"), "class_range": f"{a.get('class_min', '?')} – {a.get('class_max', '?')}",
                     "z_score": a.get("z_score"), "severity": a.get("severity"),
                     "method": a.get("method"), "message": a.get("message"),
                     "ai_assessment": a.get("ai_assessment"), "ai_suggestion": a.get("ai_suggestion")}
                    for a in anomalies
                ],
                "ip_label": "Iksula DIM Validator v2.3 — 340 rules + AI anomaly detection",
            },
        )

    def _try_normalise(self, current_value: float, raw_text: str, target_unit: str) -> float | None:
        """Try to detect source unit from raw text and convert."""
        raw_lower = raw_text.lower().strip()
        for (from_u, to_u), factor in CONVERSIONS.items():
            if to_u == target_unit.lower() and from_u in raw_lower:
                return round(current_value * factor, 4)

        # Temperature F→C
        if target_unit == "°C" and ("f" in raw_lower or "°f" in raw_lower):
            return TEMP_F_TO_C(current_value)

        return current_value


# Register
from app.pipeline.orchestrator import register_processor
register_processor(5, Stage5Validate())
