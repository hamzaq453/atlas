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
    async def stream(self, messages: list[Message], **opts: Any) -> AsyncIterator[LLMChunk]:
        raise NotImplementedError
        yield  # pragma: no cover

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError
