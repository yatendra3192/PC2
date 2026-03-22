"""Anthropic Claude adapter — calls Claude Sonnet/Opus for LLM tasks."""

import json
import time
import logging
import httpx

from app.config import settings
from app.ai.base import ModelAdapter, ModelInput, ModelOutput

logger = logging.getLogger(__name__)

ANTHROPIC_BASE = "https://api.anthropic.com/v1"


class AnthropicAdapter(ModelAdapter):

    def __init__(self):
        self.model_name = settings.anthropic_model
        self.api_key = settings.anthropic_api_key

    async def invoke(self, input: ModelInput) -> ModelOutput:
        start = time.time()
        prompt = input.prompt or f"Task: {input.task}\nData: {json.dumps(input.data)}\n\nReturn valid JSON."

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{ANTHROPIC_BASE}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["content"][0]["text"]
        tokens = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
        elapsed = int((time.time() - start) * 1000)

        # Try parse JSON
        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            value = content

        return ModelOutput(
            value=value,
            model_name=f"Claude ({self.model_name})",
            confidence=85,
            tokens_used=tokens,
            latency_ms=elapsed,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{ANTHROPIC_BASE}/messages",
                    headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": self.model_name, "max_tokens": 10, "messages": [{"role": "user", "content": "ping"}]},
                    timeout=10.0,
                )
                return resp.status_code == 200
        except Exception:
            return False
