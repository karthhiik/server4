"""Abstract base for all LLM clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: int = 0
    raw_response: Optional[Any] = None


class BaseLLMClient(ABC):
    name: str = "base"
    provider: str = "unknown"

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        ...

    async def health_check(self) -> bool:
        try:
            resp = await self.complete(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(resp.content)
        except Exception:
            return False
