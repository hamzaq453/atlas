from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from atlas.services.llm.types import LLMChunk, LLMResponse, Message


@runtime_checkable
class LLMProvider(Protocol):
    """Swappable LLM backend (Gemini today; Claude/OpenAI later)."""

    name: str
    model: str
    max_context: int

    async def complete(self, messages: list[Message], **opts: Any) -> LLMResponse: ...

    async def stream(self, messages: list[Message], **opts: Any) -> AsyncIterator[LLMChunk]: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
