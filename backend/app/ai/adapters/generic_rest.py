"""Generic REST adapter — for client-provided custom models.

Clients register their model endpoint URL + auth method.
This adapter calls any REST API that accepts JSON and returns JSON.
"""

from __future__ import annotations


import json
import time
import logging
import httpx

from app.ai.base import ModelAdapter, ModelInput, ModelOutput

logger = logging.getLogger(__name__)


class GenericRESTAdapter(ModelAdapter):

    def __init__(self, model_name: str, endpoint_url: str, api_key: str | None = None, auth_header: str = "Authorization"):
        self.model_name = model_name
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.auth_header = auth_header

    async def invoke(self, input: ModelInput) -> ModelOutput:
        start = time.time()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers[self.auth_header] = f"Bearer {self.api_key}"

        payload = {
            "task": input.task,
            "data": input.data,
            "prompt": input.prompt,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.endpoint_url, json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

        elapsed = int((time.time() - start) * 1000)

        return ModelOutput(
            value=data.get("value", data.get("result", data)),
            model_name=f"{self.model_name} (custom)",
            confidence=data.get("confidence", 75),
            tokens_used=data.get("tokens_used", 0),
            latency_ms=elapsed,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.endpoint_url.rstrip("/") + "/health", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
