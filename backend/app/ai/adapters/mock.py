"""Mock AI adapter — returns hardcoded demo outputs for the Orbit B-0624W product."""

import asyncio
from app.ai.base import ModelAdapter, ModelInput, ModelOutput

# Demo data for Orbit 24V 6-Zone Smart Irrigation Controller (B-0624W)
DEMO_EXTRACTED_FIELDS = {
    "product_name": {"value": "Orbit 24V 6-Zone Smart Irrigation Controller", "confidence": 97, "page": "1"},
    "model_number": {"value": "B-0624W", "confidence": 99, "page": "1"},
    "voltage": {"value": "24V", "confidence": 95, "page": "1", "numeric": 24},
    "zones": {"value": "6", "confidence": 96, "page": "1", "numeric": 6},
    "wifi_enabled": {"value": "Yes", "confidence": 92, "page": "2", "boolean": True},
    "ip_rating": {"value": "IP44", "confidence": 94, "page": "2"},
    "supplier_name": {"value": "Orbit Irrigation Products", "confidence": 98, "page": "1"},
}

DEMO_CLASSIFICATION = {
    "department": {"name": "Hardware & Tools", "code": "HW", "confidence": 96},
    "category": {"name": "Irrigation", "code": "HW-IRR", "confidence": 95},
    "class": {"name": "Controllers", "code": "HW-IRR-CTRL", "confidence": 94},
    "subclass": {"name": "Smart Controllers", "code": "HW-IRR-CTRL-SMART", "confidence": 94},
}

DEMO_ENRICHED_FIELDS = {
    "material": {"value": "abs_plastic", "label": "ABS Plastic", "source": "kb", "confidence": 95, "model": "Iksula KB v3.1"},
    "colour": {"value": "grey", "label": "Grey", "source": "vision", "confidence": 72, "model": "Iksula Vision v1.2"},
    "weight_kg": {"value": 0.36, "raw": "0.8 lbs", "source": "web_google", "confidence": 88, "model": "Iksula Enrichment — Irrigation v4", "url": "orbitonline.com/products/B-0624W"},
    "width_cm": {"value": 17.8, "raw": "7 in", "source": "web_google", "confidence": 85, "model": "Iksula Enrichment — Irrigation v4"},
    "depth_cm": {"value": 11.9, "raw": "4.7 in", "source": "web_google", "confidence": 85, "model": "Iksula Enrichment — Irrigation v4"},
    "height_cm": {"value": 6.1, "raw": "2.4 in", "source": "web_google", "confidence": 85, "model": "Iksula Enrichment — Irrigation v4"},
    "operating_temp_min_c": {"value": 0, "raw": "32°F", "source": "llm", "confidence": 80, "model": "GPT-4o"},
    "operating_temp_max_c": {"value": 50, "raw": "122°F", "source": "llm", "confidence": 80, "model": "GPT-4o"},
    "certifications": {"value": ["ce", "rohs"], "source": "kb", "confidence": 90, "model": "Iksula KB v3.1"},
    "compatible_valve_types": {"value": ["24vac_solenoid"], "source": "kb", "confidence": 68, "model": "Iksula KB v3.1"},
    "app_name": {"value": "Orbit B-hyve", "source": "web_marketplace", "confidence": 61, "model": "Iksula Enrichment — Irrigation v4", "url": "amazon.com/dp/B09XYZ5678"},
    "warranty_months": {"value": 24, "source": "web_google", "confidence": 87, "model": "Iksula Enrichment — Irrigation v4"},
}

DEMO_COPY = {
    "product_title": "Orbit 24V 6-Zone Smart Wi-Fi Irrigation Controller — IP44 Outdoor",
    "short_description": "Smart 6-zone irrigation controller with Wi-Fi, 24V, IP44-rated for outdoor use. Compatible with Orbit B-hyve app.",
    "long_description": "The Orbit B-0624W is a 6-zone smart irrigation controller operating on 24V with built-in Wi-Fi connectivity. IP44-rated for outdoor installation, it supports 24VAC solenoid valves and is controllable via the Orbit B-hyve app. Constructed from durable ABS plastic in grey finish. CE and RoHS certified. Operating temperature range: 0–50°C.",
}

DEMO_DEDUP = {
    "match_found": True,
    "match_type": "possible_variant",
    "similarity": 78,
    "matched_product_id": "77777777-7777-7777-7777-111111111111",
    "matched_product_name": "Orbit 4-Zone Smart Irrigation Controller",
    "matched_model": "B-0424W",
    "key_differences": {"zones": {"incoming": 6, "existing": 4}},
}

DEMO_WEB_SCRAPE = {
    "google_results": [
        {"url": "orbitonline.com/products/B-0624W", "attrs": {"weight": "0.8 lbs", "dimensions": "7 × 4.7 × 2.4 in", "app": "Orbit B-hyve"}},
        {"url": "irrigationdirect.com/orbit-b0624w", "attrs": {"operating_temp": "32–122°F", "warranty": "24 months"}},
        {"url": "homedepot.com/p/orbit-6-zone/309876", "attrs": {"color": "Grey", "certifications": "CE, RoHS"}},
    ],
    "amazon_results": [
        {"url": "amazon.com/dp/B09XYZ1234", "title": "Orbit 57946 B-hyve Smart 6-Zone...", "attrs": {"weight": "12.8 oz", "zones": "6", "voltage": "24V", "color": "Gray"}},
        {"url": "amazon.com/dp/B09XYZ5678", "title": "Orbit B-hyve 6-Station Smart...", "attrs": {"compatible": "24VAC solenoid valves", "app": "B-hyve"}},
    ],
}


class MockAdapter(ModelAdapter):
    """Returns hardcoded demo data with realistic delays."""

    def __init__(self, model_name: str = "Mock"):
        self.model_name = model_name

    async def invoke(self, input: ModelInput) -> ModelOutput:
        task = input.task

        if task == "extract_fields":
            await asyncio.sleep(0.8)  # Simulate OCR + parsing
            return ModelOutput(
                value=DEMO_EXTRACTED_FIELDS,
                model_name="Iksula OCR Engine v2",
                confidence=95,
                latency_ms=800,
            )

        elif task == "classify":
            await asyncio.sleep(0.6)
            return ModelOutput(
                value=DEMO_CLASSIFICATION,
                model_name="Iksula Retail Taxonomy v4.2",
                confidence=94,
                latency_ms=600,
            )

        elif task == "dedup":
            await asyncio.sleep(1.0)
            return ModelOutput(
                value=DEMO_DEDUP,
                model_name="Iksula Dedup Model v1.0",
                confidence=78,
                latency_ms=1000,
            )

        elif task == "enrich":
            await asyncio.sleep(1.2)
            return ModelOutput(
                value=DEMO_ENRICHED_FIELDS,
                model_name="Iksula KB v3.1",
                confidence=85,
                latency_ms=1200,
            )

        elif task == "generate_copy":
            await asyncio.sleep(1.0)
            return ModelOutput(
                value=DEMO_COPY,
                model_name="GPT-4o",
                confidence=90,
                latency_ms=1000,
                metadata={"prompt_template": "Iksula Copy Prompt — Irrigation Controllers v3.0 — SiteOne edition"},
            )

        elif task == "web_scrape":
            await asyncio.sleep(1.5)
            return ModelOutput(
                value=DEMO_WEB_SCRAPE,
                model_name="Iksula Web Scraper v1.0",
                confidence=80,
                latency_ms=1500,
            )

        else:
            return ModelOutput(value=None, model_name="Mock", confidence=0)

    async def health_check(self) -> bool:
        return True
