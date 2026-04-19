from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from atlas.services.llm.types import LLMChunk, LLMResponse, Message


class LLMProvider(ABC):
    """Swappable LLM backend (Gemini today; Claude/OpenAI later)."""

    name: str
    model: str
    max_context: int

    @abstractmethod
    async def complete(self, messages: list[Message], **opts: Any) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def stream(self, messages: list[Message], **opts: Any) -> AsyncIterator[LLMChunk]:
        """Default non-streaming fallback: one chunk from `complete`."""
        response = await self.complete(messages, **opts)
        yield LLMChunk(delta=response.content, finish_reason="STOP", usage=response.usage)
