from __future__ import annotations

import pytest

from atlas.config import Settings
from atlas.services.llm import build_llm, reset_llm_for_tests
from atlas.services.llm.fake_provider import FakeLLM
from atlas.services.llm.gemini import GeminiProvider
from atlas.services.llm.groq import GroqProvider


def test_build_llm_returns_gemini_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_USE_FAKE_LLM", raising=False)
    settings = Settings(
        database_url="postgresql+asyncpg://a:b@localhost:5432/db",
        test_database_url="postgresql+asyncpg://a:b@localhost:5432/db",
        gemini_api_key="test-key",
        llm_provider="gemini",
    )
    provider = build_llm(settings)
    assert isinstance(provider, GeminiProvider)
    reset_llm_for_tests()


def test_build_llm_fake_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_USE_FAKE_LLM", "1")
    settings = Settings(
        database_url="postgresql+asyncpg://a:b@localhost:5432/db",
        test_database_url="postgresql+asyncpg://a:b@localhost:5432/db",
        llm_provider="gemini",
    )
    provider = build_llm(settings)
    assert isinstance(provider, FakeLLM)
    reset_llm_for_tests()


def test_build_llm_returns_groq_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_USE_FAKE_LLM", raising=False)
    settings = Settings(
        database_url="postgresql+asyncpg://a:b@localhost:5432/db",
        test_database_url="postgresql+asyncpg://a:b@localhost:5432/db",
        groq_api_key="gsk_test",
        llm_provider="groq",
    )
    provider = build_llm(settings)
    assert isinstance(provider, GroqProvider)
    reset_llm_for_tests()


def test_build_llm_claude_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_USE_FAKE_LLM", raising=False)
    settings = Settings(
        database_url="postgresql+asyncpg://a:b@localhost:5432/db",
        test_database_url="postgresql+asyncpg://a:b@localhost:5432/db",
        llm_provider="claude",
    )
    with pytest.raises(NotImplementedError, match="claude"):
        build_llm(settings)
