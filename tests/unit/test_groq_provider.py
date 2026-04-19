from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas.services.llm.groq import GroqProvider
from atlas.services.llm.types import Message


@pytest.mark.asyncio
async def test_groq_complete_maps_openai_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_USE_FAKE_LLM", raising=False)

    message = SimpleNamespace(
        content="hello",
        tool_calls=None,
    )
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
    )

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("atlas.services.llm.groq.AsyncOpenAI", return_value=fake_client):
        provider = GroqProvider(api_key="gsk_x", model="qwen/qwen3-32b")
        result = await provider.complete([Message(role="user", content="hi")])

    assert result.content == "hello"
    assert result.usage is not None
    assert result.usage.get("total_tokens") == 3


@pytest.mark.asyncio
async def test_groq_stream_yields_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_USE_FAKE_LLM", raising=False)

    delta = SimpleNamespace(content="a")
    chunk = SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=None)], usage=None)

    async def fake_stream() -> AsyncIterator[Any]:
        yield chunk

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_stream())

    with patch("atlas.services.llm.groq.AsyncOpenAI", return_value=fake_client):
        provider = GroqProvider(api_key="gsk_x", model="qwen/qwen3-32b")
        chunks = [c async for c in provider.stream([Message(role="user", content="hi")])]

    assert len(chunks) == 1
    assert chunks[0].delta == "a"
