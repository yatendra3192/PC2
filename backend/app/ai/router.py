"""Model router — selects the right adapter based on task, available keys, and config.

Priority:
1. If DEMO_MODE=true → always use MockAdapter (hardcoded demo data)
2. If OpenAI key available → use OpenAIAdapter for LLM/vision/embedding tasks
3. If Anthropic key available → use as fallback for LLM tasks
4. If no keys → fall back to MockAdapter with a warning
"""

from __future__ import annotations


import logging
from app.config import settings
from app.ai.base import ModelInput, ModelOutput
from app.ai.adapters.mock import MockAdapter

logger = logging.getLogger(__name__)

# Lazy-loaded adapters
_mock = MockAdapter()
_openai = None
_anthropic = None
_kb = None


def _get_openai():
    global _openai
    if _openai is None and settings.has_openai:
        from app.ai.adapters.openai_adapter import OpenAIAdapter
        _openai = OpenAIAdapter()
        logger.info(f"OpenAI adapter initialized: model={settings.openai_model}")
    return _openai


def _get_kb():
    global _kb
    if _kb is None:
        from app.ai.adapters.iksula_kb import IksulaKBAdapter
        _kb = IksulaKBAdapter()
    return _kb


def _get_anthropic():
    global _anthropic
    if _anthropic is None and settings.has_anthropic:
        from app.ai.adapters.anthropic_adapter import AnthropicAdapter
        _anthropic = AnthropicAdapter()
        logger.info(f"Anthropic adapter initialized: model={settings.anthropic_model}")
    return _anthropic


# Task → adapter routing
LLM_TASKS = {"extract_fields", "classify", "enrich", "generate_copy", "dedup", "validate_dims", "map_template"}
EMBEDDING_TASKS = {"generate_embedding"}
VISION_TASKS = {"analyze_image", "read_label"}
MOCK_ONLY_TASKS = {"web_scrape"}  # Web scraping uses scraper module, not AI adapter


async def invoke_model(task: str, data: dict | None = None, prompt: str | None = None) -> ModelOutput:
    """Route a task to the appropriate model adapter."""
    input = ModelInput(task=task, data=data or {}, prompt=prompt)

    # 1. Demo mode — always mock
    if settings.demo_mode:
        return await _mock.invoke(input)

    # 2. Web scrape tasks — use mock for now (real scraper is separate module)
    if task in MOCK_ONLY_TASKS:
        return await _mock.invoke(input)

    # 3. KB tasks — always use real DB lookup (no API key needed)
    if task in ("picklist_match", "enrich") and task != "generate_copy":
        kb = _get_kb()
        if kb:
            try:
                kb_result = await kb.invoke(input)
                if kb_result.value:
                    return kb_result
            except Exception as e:
                logger.warning(f"KB lookup failed: {e}")
            # KB didn't find it — fall through to LLM

    # 4. Try real LLM adapters
    openai = _get_openai()
    anthropic = _get_anthropic()

    if openai and task in (LLM_TASKS | EMBEDDING_TASKS | VISION_TASKS):
        try:
            result = await openai.invoke(input)
            logger.info(f"Real AI call: task={task}, model={result.model_name}, latency={result.latency_ms}ms")
            return result
        except Exception as e:
            logger.error(f"OpenAI call failed for task={task}: {e}")
            # Try Anthropic as fallback
            if anthropic and task in LLM_TASKS:
                try:
                    result = await anthropic.invoke(input)
                    logger.info(f"Anthropic fallback: task={task}, model={result.model_name}")
                    return result
                except Exception as e2:
                    logger.error(f"Anthropic fallback also failed: {e2}")
            logger.warning(f"All adapters failed for task={task}, using MockAdapter")
            return await _mock.invoke(input)

    if anthropic and task in LLM_TASKS:
        try:
            result = await anthropic.invoke(input)
            return result
        except Exception as e:
            logger.error(f"Anthropic call failed: {e}")
            return await _mock.invoke(input)

    # 4. No real adapter available — fall back to mock with warning
    logger.warning(f"No real adapter for task={task}, using MockAdapter. Set API keys in .env to use real models.")
    return await _mock.invoke(input)


async def check_model_health() -> dict:
    """Check which adapters are available and healthy."""
    status = {
        "demo_mode": settings.demo_mode,
        "openai": {"configured": settings.has_openai, "healthy": False, "model": settings.openai_model},
        "anthropic": {"configured": settings.has_anthropic, "healthy": False, "model": settings.anthropic_model},
        "serpapi": {"configured": settings.has_serpapi},
    }

    if settings.has_openai:
        openai = _get_openai()
        if openai:
            status["openai"]["healthy"] = await openai.health_check()

    return status
