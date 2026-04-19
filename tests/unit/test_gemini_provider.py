from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from atlas.services.llm.gemini import GeminiProvider
from atlas.services.llm.types import Message


@pytest.mark.asyncio
async def test_gemini_complete_maps_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_USE_FAKE_LLM", raising=False)

    fake_response = SimpleNamespace(
        text="hello",
        candidates=[],
        usage_metadata=SimpleNamespace(
            prompt_token_count=3,
            candidates_token_count=2,
            total_token_count=5,
        ),
    )

    fake_model = MagicMock()
    fake_model.generate_content.return_value = fake_response

    with patch("atlas.services.llm.gemini.genai.GenerativeModel", return_value=fake_model):
        provider = GeminiProvider(
            api_key="k",
            chat_model="gemini-test",
            embedding_model="models/text-embedding-004",
        )
        result = await provider.complete([Message(role="user", content="hi")])

    assert result.content == "hello"
    assert result.usage is not None
    assert result.usage.get("total_token_count") == 5


@pytest.mark.asyncio
async def test_gemini_stream_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_USE_FAKE_LLM", raising=False)

    chunk = SimpleNamespace(text="a", candidates=[], usage_metadata=None)

    fake_model = MagicMock()
    fake_model.generate_content.return_value = [chunk]

    with patch("atlas.services.llm.gemini.genai.GenerativeModel", return_value=fake_model):
        provider = GeminiProvider(
            api_key="k",
            chat_model="gemini-test",
            embedding_model="models/text-embedding-004",
        )
        chunks = [c async for c in provider.stream([Message(role="user", content="hi")])]

    assert len(chunks) == 1
    assert chunks[0].delta == "a"
