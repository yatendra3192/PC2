"""Maps raw scraped attributes to Iksula normalised fields.

Uses supplier_field_mappings + fuzzy matching + synonym lookup.
"""

from __future__ import annotations


import re
import logging
from app.db.client import fetch_all

logger = logging.getLogger(__name__)

# Common unit conversions
CONVERSIONS = {
    ("lbs", "kg"): lambda v: v * 0.453592,
    ("oz", "kg"): lambda v: v * 0.0283495,
    ("in", "cm"): lambda v: v * 2.54,
    ("inches", "cm"): lambda v: v * 2.54,
    ("f", "c"): lambda v: (v - 32) * 5 / 9,
    ("°f", "°c"): lambda v: (v - 32) * 5 / 9,
}


class TemplateMapper:
    async def map_to_iksula(self, raw_attrs: dict, taxonomy_node_id: str) -> dict:
        """Map scraped raw values to Iksula normalised attributes."""
        # Load class attributes with allowed values
        attrs = await fetch_all(
            """SELECT ica.id, ica.attribute_code, ica.attribute_name, ica.data_type, ica.unit
               FROM iksula_class_attributes ica
               WHERE ica.taxonomy_node_id = $1::uuid""",
            taxonomy_node_id,
        )

        # Load synonyms for matching
        synonyms = {}
        for attr in attrs:
            vals = await fetch_all(
                "SELECT value_code, synonyms FROM iksula_allowed_values WHERE attribute_id = $1::uuid",
                str(attr["id"]),
            )
            for v in vals:
                for syn in (v["synonyms"] or []):
                    synonyms[syn.lower()] = (attr["attribute_code"], v["value_code"])

        mapped = {}
        for raw_key, raw_value in raw_attrs.items():
            # Try direct match
            attr = _find_attribute(raw_key, attrs)
            if attr:
                normalised = _normalise_value(raw_value, attr["data_type"], attr["unit"])
                mapped[attr["attribute_code"]] = normalised
                continue

            # Try synonym match on value
            if isinstance(raw_value, str) and raw_value.lower() in synonyms:
                attr_code, value_code = synonyms[raw_value.lower()]
                mapped[attr_code] = value_code

        return mapped


def _find_attribute(raw_key: str, attrs: list) -> dict | None:
    """Fuzzy match a raw field name to an Iksula attribute."""
    key = raw_key.lower().strip().replace(" ", "_").replace("-", "_")
    for attr in attrs:
        if key == attr["attribute_code"]:
            return dict(attr)
        if key in attr["attribute_name"].lower().replace(" ", "_"):
            return dict(attr)
    return None


def _normalise_value(raw_value: str, data_type: str, target_unit: str | None) -> str | float | bool | None:
    """Convert raw value to normalised format."""
    if not raw_value:
        return None

    raw = str(raw_value).strip()

    if data_type == "boolean":
        return raw.lower() in ("yes", "true", "1", "y")

    if data_type in ("integer", "decimal", "measurement"):
        # Extract numeric + unit
        match = re.search(r"([\d.]+)\s*(\w+)?", raw)
        if match:
            numeric = float(match.group(1))
            unit = (match.group(2) or "").lower()
            if target_unit and unit:
                converter = CONVERSIONS.get((unit, target_unit.lower()))
                if converter:
                    numeric = converter(numeric)
            return round(numeric, 4) if data_type == "decimal" else numeric

    return raw
