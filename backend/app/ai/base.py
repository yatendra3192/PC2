from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ModelInput:
    task: str  # e.g. "extract_fields", "classify", "generate_copy"
    data: dict[str, Any] = None
    prompt: str | None = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass
class ModelOutput:
    value: Any
    model_name: str
    confidence: float = 0.0
    tokens_used: int = 0
    latency_ms: int = 0
    metadata: dict | None = None


class ModelAdapter(ABC):
    """Unified interface for all AI/ML models."""

    model_name: str

    @abstractmethod
    async def invoke(self, input: ModelInput) -> ModelOutput:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass
