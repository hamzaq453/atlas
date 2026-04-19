from __future__ import annotations

from typing import Any

from atlas.services.llm.base import LLMProvider
from atlas.services.llm.types import LLMResponse, Message


class FakeLLM(LLMProvider):
    """Deterministic LLM stub for tests (enabled via ATLAS_USE_FAKE_LLM=1)."""

    name = "fake"
    model = "fake"
    max_context = 99_999

    async def complete(self, messages: list[Message], **opts: Any) -> LLMResponse:
        last = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return LLMResponse(content=f"echo:{last}", tool_calls=[], usage={"total_token_count": 1})

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 768 for _ in texts]
