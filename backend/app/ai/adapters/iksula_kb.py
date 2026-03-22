"""Iksula Knowledge Base adapter — real DB lookups against picklist tables.

This is NOT an external API call — it queries the local database for:
- Attribute picklist matches (iksula_allowed_values)
- Synonym matching
- Class-specific attribute validation
"""

import logging
from app.ai.base import ModelAdapter, ModelInput, ModelOutput
from app.db.client import fetch_all, fetch_one

logger = logging.getLogger(__name__)


class IksulaKBAdapter(ModelAdapter):

    def __init__(self):
        self.model_name = "Iksula KB v3.1"

    async def invoke(self, input: ModelInput) -> ModelOutput:
        if input.task == "enrich":
            return await self._enrich_from_kb(input)
        elif input.task == "picklist_match":
            return await self._picklist_match(input)
        else:
            return ModelOutput(value=None, model_name=self.model_name, confidence=0)

    async def _enrich_from_kb(self, input: ModelInput) -> ModelOutput:
        """Fill missing attributes from KB picklist + synonym matching."""
        missing_attrs = input.data.get("missing_attributes", [])
        taxonomy_node_id = input.data.get("taxonomy_node_id")

        if not taxonomy_node_id:
            return ModelOutput(value={}, model_name=self.model_name, confidence=0)

        enriched = {}

        for attr_code in missing_attrs:
            # Get attribute definition
            attr = await fetch_one(
                """SELECT id, attribute_code, data_type
                   FROM iksula_class_attributes
                   WHERE attribute_code = $1 AND taxonomy_node_id = $2::uuid""",
                attr_code, taxonomy_node_id,
            )
            if not attr:
                continue

            # For enum/multi_enum, check if there's a default or most common value
            if attr["data_type"] in ("enum", "multi_enum"):
                values = await fetch_all(
                    "SELECT value_code, value_label FROM iksula_allowed_values WHERE attribute_id = $1::uuid AND is_active = true ORDER BY sort_order LIMIT 5",
                    str(attr["id"]),
                )
                if values:
                    # Return the first value as a suggestion (in production, use frequency analysis)
                    enriched[attr_code] = {
                        "value": values[0]["value_code"] if attr["data_type"] == "enum" else [v["value_code"] for v in values[:2]],
                        "label": values[0]["value_label"],
                        "source": "kb",
                        "confidence": 70,
                        "model": self.model_name,
                        "picklist": [{"code": v["value_code"], "label": v["value_label"]} for v in values],
                    }

        return ModelOutput(value=enriched, model_name=self.model_name, confidence=70)

    async def _picklist_match(self, input: ModelInput) -> ModelOutput:
        """Match a raw value against picklist + synonyms."""
        attr_code = input.data.get("attribute_code")
        raw_value = input.data.get("value", "")
        taxonomy_node_id = input.data.get("taxonomy_node_id")

        if not attr_code or not raw_value:
            return ModelOutput(value=None, model_name=self.model_name, confidence=0)

        # Find the attribute
        attr = await fetch_one(
            "SELECT id FROM iksula_class_attributes WHERE attribute_code = $1 AND taxonomy_node_id = $2::uuid",
            attr_code, taxonomy_node_id,
        )
        if not attr:
            return ModelOutput(value=None, model_name=self.model_name, confidence=0)

        # Check direct match
        direct = await fetch_one(
            "SELECT value_code, value_label FROM iksula_allowed_values WHERE attribute_id = $1::uuid AND (value_code = $2 OR value_label = $2)",
            str(attr["id"]), raw_value,
        )
        if direct:
            return ModelOutput(value={"code": direct["value_code"], "label": direct["value_label"]}, model_name=self.model_name, confidence=98)

        # Check synonym match
        synonym = await fetch_one(
            "SELECT value_code, value_label FROM iksula_allowed_values WHERE attribute_id = $1::uuid AND $2 = ANY(synonyms)",
            str(attr["id"]), raw_value.lower(),
        )
        if synonym:
            return ModelOutput(value={"code": synonym["value_code"], "label": synonym["value_label"]}, model_name=self.model_name, confidence=90)

        # Case-insensitive partial match
        partial = await fetch_one(
            "SELECT value_code, value_label FROM iksula_allowed_values WHERE attribute_id = $1::uuid AND LOWER(value_label) LIKE '%' || $2 || '%'",
            str(attr["id"]), raw_value.lower(),
        )
        if partial:
            return ModelOutput(value={"code": partial["value_code"], "label": partial["value_label"]}, model_name=self.model_name, confidence=75)

        return ModelOutput(value=None, model_name=self.model_name, confidence=0)

    async def health_check(self) -> bool:
        try:
            row = await fetch_one("SELECT COUNT(*) as cnt FROM iksula_allowed_values")
            return row["cnt"] > 0
        except Exception:
            return False
