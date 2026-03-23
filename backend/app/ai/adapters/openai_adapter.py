"""Real OpenAI adapter — calls GPT-4o for LLM tasks, Vision, and Embeddings."""

from __future__ import annotations


import json
import time
import logging
import httpx

from app.config import settings
from app.ai.base import ModelAdapter, ModelInput, ModelOutput

logger = logging.getLogger(__name__)

OPENAI_BASE = "https://api.openai.com/v1"


class OpenAIAdapter(ModelAdapter):
    """Production adapter for OpenAI models (GPT-4o, embeddings)."""

    def __init__(self):
        self.model_name = settings.openai_model
        self.api_key = settings.openai_api_key

    async def invoke(self, input: ModelInput) -> ModelOutput:
        start = time.time()

        if input.task == "extract_fields":
            result = await self._extract_fields(input)
        elif input.task == "classify":
            result = await self._classify(input)
        elif input.task == "enrich":
            result = await self._enrich(input)
        elif input.task == "generate_copy":
            result = await self._generate_copy(input)
        elif input.task == "dedup":
            result = await self._dedup(input)
        elif input.task == "generate_embedding":
            result = await self._generate_embedding(input)
        else:
            result = await self._generic_completion(input)

        elapsed = int((time.time() - start) * 1000)
        result.latency_ms = elapsed
        return result

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{OPENAI_BASE}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=5.0,
                )
                return resp.status_code == 200
        except Exception:
            return False

    # ── Task-specific methods ──

    async def _extract_fields(self, input: ModelInput) -> ModelOutput:
        """Extract product attributes from text/OCR content."""
        target_attrs = input.data.get("target_attributes", [])
        attr_list = "\n".join([
            f"- {a['attribute_code']} ({a['attribute_name']}): type={a['data_type']}, unit={a.get('unit', 'none')}, mandatory={a.get('is_mandatory', False)}"
            for a in target_attrs
        ]) if target_attrs else "Extract all product attributes you can find."

        prompt = f"""You are a product data extraction engine. Extract structured product attributes from the provided content.

Target attributes to extract:
{attr_list}

Also extract these identity fields if found:
- product_name
- model_number
- supplier_name
- brand
- sku, upc, ean

For each field you extract, provide:
- "value": the extracted value
- "confidence": 0-100 how confident you are
- "page": page reference if applicable

Return JSON object where keys are attribute codes and values are objects with value/confidence/page.
If a field has a numeric value, include "numeric" key with the number.
If boolean, include "boolean" key.

Content to extract from:
{input.data.get("content", input.data.get("product_name", "No content provided"))}"""

        response = await self._chat_completion(prompt, response_format="json_object")
        return ModelOutput(
            value=response,
            model_name=f"GPT-4o ({settings.openai_model})",
            confidence=85,
        )

    async def _classify(self, input: ModelInput) -> ModelOutput:
        """Classify product into retail taxonomy."""
        prompt = f"""You are a retail product taxonomy classifier. Classify this product into a 4-level hierarchy.

Product: {input.data.get("product_name", "")}
Model: {input.data.get("model_number", "")}
Known attributes: {json.dumps(input.data.get("known_attributes", {}))}

Return JSON with this exact structure:
{{
  "department": {{"name": "...", "code": "...", "confidence": 0-100}},
  "category": {{"name": "...", "code": "...", "confidence": 0-100}},
  "class": {{"name": "...", "code": "...", "confidence": 0-100}},
  "subclass": {{"name": "...", "code": "...", "confidence": 0-100}}
}}

Use retail taxonomy standards. Common departments: Hardware & Tools, Plumbing, Electrical, Outdoor Living, Building Materials."""

        response = await self._chat_completion(prompt, response_format="json_object")
        return ModelOutput(
            value=response,
            model_name=f"GPT-4o ({settings.openai_model})",
            confidence=response.get("subclass", {}).get("confidence", 80) if isinstance(response, dict) else 80,
        )

    async def _enrich(self, input: ModelInput) -> ModelOutput:
        """Fill missing product attributes using LLM inference."""
        missing = input.data.get("missing_attributes", [])
        prompt = f"""You are a product data enrichment engine. For the following product, infer the missing attribute values.

Product: {input.data.get("product_name", "")}
Model: {input.data.get("model_number", "")}
Known attributes: {json.dumps(input.data.get("known_attributes", {}))}

Missing attributes to fill:
{json.dumps(missing)}

For each attribute, return:
- "value": the inferred value (use standard units: kg, cm, °C)
- "source": "llm" (since you're inferring)
- "confidence": 0-100 how certain you are
- "model": "GPT-4o"

Return JSON object where keys are attribute codes.
Only include attributes you can reasonably infer. Don't guess blindly."""

        response = await self._chat_completion(prompt, response_format="json_object")
        return ModelOutput(
            value=response,
            model_name=f"GPT-4o ({settings.openai_model})",
            confidence=70,
        )

    async def _generate_copy(self, input: ModelInput) -> ModelOutput:
        """Generate product title, short description, long description."""
        prompt = input.prompt or f"""Generate professional B2B product copy for a retail catalog.

Product: {input.data.get("product_name", "")}
Model: {input.data.get("model_number", "")}
Key specs: {json.dumps(input.data.get("specs", {}))}

Return JSON:
{{
  "product_title": "max 80 chars, SEO-optimised, include key specs",
  "short_description": "max 150 chars, feature-led, professional tone",
  "long_description": "max 400 chars, spec-heavy, B2B tone, include all key specifications"
}}"""

        response = await self._chat_completion(prompt, response_format="json_object")
        return ModelOutput(
            value=response,
            model_name=f"GPT-4o ({settings.openai_model})",
            confidence=90,
            metadata={"prompt_template": "GPT-4o Copy Generation"},
        )

    async def _dedup(self, input: ModelInput) -> ModelOutput:
        """Compare incoming product against potential duplicate."""
        incoming = f"Product: {input.data.get('product_name', '')}, Model: {input.data.get('model_number', '')}"
        exact_match = input.data.get('exact_match')

        if exact_match:
            match_info = f"Candidate match: {input.data.get('exact_match_name', '')}, Model: {input.data.get('exact_match_model', '')}"
        else:
            match_info = "No exact ID match found in the catalog."

        prompt = f"""You are a product deduplication engine for a retail catalog.

Compare the incoming product against the candidate match (if any) and determine:
1. Are these the same product (duplicate)?
2. Are these variants of the same product (e.g., different size/color)?
3. Are these completely different products?

Incoming product:
{incoming}
SKU: {input.data.get('sku', 'N/A')}
Brand: {input.data.get('brand', 'N/A')}

{match_info}

Return JSON:
{{
  "match_found": true/false,
  "match_type": "likely_duplicate" or "possible_variant" or "new_item",
  "similarity": 0-100,
  "matched_product_id": null,
  "key_differences": {{}}
}}

If no candidate match exists, return match_found=false, similarity=0, match_type="new_item"."""

        response = await self._chat_completion(prompt, response_format="json_object")
        if isinstance(response, dict) and exact_match:
            response["matched_product_id"] = exact_match
        return ModelOutput(
            value=response,
            model_name=f"GPT-4o ({settings.openai_model})",
            confidence=response.get("similarity", 0) if isinstance(response, dict) else 50,
        )

    async def _generate_embedding(self, input: ModelInput) -> ModelOutput:
        """Generate vector embedding for dedup/similarity search."""
        text = input.data.get("text", "")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{OPENAI_BASE}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_embedding_model,
                    "input": text,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

        embedding = data["data"][0]["embedding"]
        tokens = data["usage"]["total_tokens"]

        return ModelOutput(
            value=embedding,
            model_name=settings.openai_embedding_model,
            confidence=100,
            tokens_used=tokens,
        )

    async def _generic_completion(self, input: ModelInput) -> ModelOutput:
        """Generic chat completion for any task."""
        prompt = input.prompt or f"Task: {input.task}\nData: {json.dumps(input.data)}"
        response = await self._chat_completion(prompt)
        return ModelOutput(
            value=response,
            model_name=f"GPT-4o ({settings.openai_model})",
            confidence=75,
        )

    # ── Core API call ──

    async def _chat_completion(self, prompt: str, response_format: str | None = None) -> dict | str:
        """Make a chat completion API call."""
        body: dict = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "You are a precise product data processing assistant. Always return valid JSON when asked."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 2000,
        }

        if response_format == "json_object":
            body["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{OPENAI_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        tokens = data["usage"]["total_tokens"]

        logger.info(f"OpenAI call: model={settings.openai_model}, tokens={tokens}")

        # Try to parse as JSON
        if response_format == "json_object":
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, returning raw string")
                return {"raw": content}

        return content
