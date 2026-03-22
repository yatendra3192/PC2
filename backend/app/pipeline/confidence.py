"""Confidence score calculation and explanation engine.

Every confidence score has:
1. A numeric value (0-100)
2. A breakdown into components
3. A human-readable explanation of what it means and how it was calculated
"""

from __future__ import annotations


from dataclasses import dataclass


@dataclass
class ConfidenceScore:
    composite: float
    breakdown: dict[str, float]
    explanation: str
    factors: list[str]


# Stage-specific confidence calculators

def stage1_extraction_confidence(
    ocr_quality: float,
    field_match: float,
    value_completeness: float,
    weights: dict | None = None,
) -> ConfidenceScore:
    """Stage 1: How reliable was the extraction?"""
    w = weights or {"ocr_quality": 0.40, "field_match": 0.35, "value_completeness": 0.25}

    composite = (
        ocr_quality * w["ocr_quality"]
        + field_match * w["field_match"]
        + value_completeness * w["value_completeness"]
    )

    factors = []
    if ocr_quality >= 90:
        factors.append(f"OCR quality is high ({ocr_quality}%) — text was clearly readable")
    elif ocr_quality >= 70:
        factors.append(f"OCR quality is moderate ({ocr_quality}%) — some characters may be uncertain")
    else:
        factors.append(f"OCR quality is low ({ocr_quality}%) — source document was hard to read")

    if field_match >= 90:
        factors.append(f"Field matching is confident ({field_match}%) — value clearly maps to this attribute")
    else:
        factors.append(f"Field matching is uncertain ({field_match}%) — value could map to multiple attributes")

    if value_completeness >= 90:
        factors.append("Value appears complete — no truncation detected")
    else:
        factors.append(f"Value may be partial ({value_completeness}%) — could be truncated or incomplete")

    explanation = (
        f"Confidence {composite:.0f}%: Calculated from OCR quality ({ocr_quality}% × {w['ocr_quality']:.0%}), "
        f"field match certainty ({field_match}% × {w['field_match']:.0%}), "
        f"and value completeness ({value_completeness}% × {w['value_completeness']:.0%})."
    )

    return ConfidenceScore(
        composite=round(composite, 1),
        breakdown={"ocr_quality": ocr_quality, "field_match": field_match, "value_completeness": value_completeness},
        explanation=explanation,
        factors=factors,
    )


def stage2_classification_confidence(
    model_confidence: float,
    taxonomy_depth: float,
    attribute_alignment: float,
    weights: dict | None = None,
) -> ConfidenceScore:
    """Stage 2: How certain is the taxonomy placement?"""
    w = weights or {"model_confidence": 0.50, "taxonomy_depth": 0.30, "attribute_alignment": 0.20}

    composite = (
        model_confidence * w["model_confidence"]
        + taxonomy_depth * w["taxonomy_depth"]
        + attribute_alignment * w["attribute_alignment"]
    )

    factors = []
    if model_confidence >= 90:
        factors.append(f"Classification model is highly confident ({model_confidence}%) — strong match to training data")
    elif model_confidence >= 75:
        factors.append(f"Classification model is moderately confident ({model_confidence}%) — product matches patterns but has some ambiguity")
    else:
        factors.append(f"Classification model is uncertain ({model_confidence}%) — product could belong to multiple categories")

    if taxonomy_depth >= 90:
        factors.append(f"Sub-class assignment is confident ({taxonomy_depth}%) — specific category identified")
    else:
        factors.append(f"Sub-class is less certain ({taxonomy_depth}%) — department/category are clear but sub-class has alternatives")

    if attribute_alignment >= 80:
        factors.append(f"Extracted attributes align well ({attribute_alignment}%) with expected attributes for this class")
    else:
        factors.append(f"Attribute alignment is weak ({attribute_alignment}%) — product has unexpected attributes for this class")

    explanation = (
        f"Confidence {composite:.0f}%: Calculated from model confidence ({model_confidence}% × {w['model_confidence']:.0%}), "
        f"taxonomy depth match ({taxonomy_depth}% × {w['taxonomy_depth']:.0%}), "
        f"and attribute alignment ({attribute_alignment}% × {w['attribute_alignment']:.0%}). "
        f"Taxonomy: Iksula Retail Taxonomy v4.2, 847 classes."
    )

    return ConfidenceScore(
        composite=round(composite, 1),
        breakdown={"model_confidence": model_confidence, "taxonomy_depth": taxonomy_depth, "attribute_alignment": attribute_alignment},
        explanation=explanation,
        factors=factors,
    )


def stage3_dedup_confidence(
    exact_match: float,
    semantic_similarity: float,
    attribute_overlap: float,
    weights: dict | None = None,
) -> ConfidenceScore:
    """Stage 3: How similar is the match?"""
    w = weights or {"exact_match": 0.40, "semantic_similarity": 0.35, "attribute_overlap": 0.25}

    composite = (
        exact_match * w["exact_match"]
        + semantic_similarity * w["semantic_similarity"]
        + attribute_overlap * w["attribute_overlap"]
    )

    factors = []
    if exact_match > 0:
        factors.append(f"Exact identifier match ({exact_match}%) — SKU, UPC, or model number matches an existing record")
    else:
        factors.append("No exact identifier match — SKU/UPC/EAN are unique")

    if semantic_similarity >= 80:
        factors.append(f"Name similarity is high ({semantic_similarity}%) — product names are semantically very similar")
    elif semantic_similarity >= 60:
        factors.append(f"Name similarity is moderate ({semantic_similarity}%) — products share key terms but differ in specifics")
    else:
        factors.append(f"Name similarity is low ({semantic_similarity}%) — product names are distinct")

    if attribute_overlap >= 70:
        factors.append(f"Attribute overlap is high ({attribute_overlap}%) — most attribute values match the existing record")
    else:
        factors.append(f"Attribute overlap is partial ({attribute_overlap}%) — some attributes match but key differences exist")

    explanation = (
        f"Similarity {composite:.0f}%: Calculated from exact ID match ({exact_match}% × {w['exact_match']:.0%}), "
        f"semantic name similarity ({semantic_similarity}% × {w['semantic_similarity']:.0%}), "
        f"and attribute overlap ({attribute_overlap}% × {w['attribute_overlap']:.0%}). "
        f"Dedup model trained on 12M retail product pairs."
    )

    return ConfidenceScore(
        composite=round(composite, 1),
        breakdown={"exact_match": exact_match, "semantic_similarity": semantic_similarity, "attribute_overlap": attribute_overlap},
        explanation=explanation,
        factors=factors,
    )


def stage4_enrichment_confidence(
    source_reliability: float,
    picklist_consistency: float,
    multi_source_agreement: float,
    weights: dict | None = None,
) -> ConfidenceScore:
    """Stage 4: How trustworthy is the enriched value?"""
    w = weights or {"source_reliability": 0.40, "picklist_consistency": 0.35, "multi_source_agreement": 0.25}

    composite = (
        source_reliability * w["source_reliability"]
        + picklist_consistency * w["picklist_consistency"]
        + multi_source_agreement * w["multi_source_agreement"]
    )

    source_labels = {
        100: "human entry (highest reliability)",
        95: "Iksula KB picklist match (very high)",
        85: "PDF/OCR extraction (high)",
        80: "supplier CSV data (high)",
        75: "image/vision analysis (moderate-high)",
        65: "LLM inference (moderate)",
        60: "web lookup (moderate)",
    }
    nearest = min(source_labels.keys(), key=lambda k: abs(k - source_reliability))
    source_desc = source_labels[nearest]

    factors = [f"Source reliability: {source_reliability}% — {source_desc}"]

    if picklist_consistency >= 90:
        factors.append(f"Picklist match: {picklist_consistency}% — value matches an approved entry in the Iksula attribute dictionary")
    elif picklist_consistency >= 70:
        factors.append(f"Picklist match: {picklist_consistency}% — value is similar to approved entries but not exact")
    else:
        factors.append(f"Picklist match: {picklist_consistency}% — value is not in the approved picklist for this class")

    if multi_source_agreement >= 80:
        factors.append(f"Multi-source agreement: {multi_source_agreement}% — multiple independent sources confirm this value")
    elif multi_source_agreement >= 50:
        factors.append(f"Multi-source agreement: {multi_source_agreement}% — some sources agree, others differ")
    else:
        factors.append(f"Multi-source agreement: {multi_source_agreement}% — single source only, no independent confirmation")

    explanation = (
        f"Confidence {composite:.0f}%: Calculated from source reliability ({source_reliability}% × {w['source_reliability']:.0%}), "
        f"picklist consistency ({picklist_consistency}% × {w['picklist_consistency']:.0%}), "
        f"and multi-source agreement ({multi_source_agreement}% × {w['multi_source_agreement']:.0%})."
    )

    return ConfidenceScore(
        composite=round(composite, 1),
        breakdown={"source_reliability": source_reliability, "picklist_consistency": picklist_consistency, "multi_source_agreement": multi_source_agreement},
        explanation=explanation,
        factors=factors,
    )
