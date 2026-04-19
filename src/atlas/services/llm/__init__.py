from __future__ import annotations

import os

from atlas.config import Settings, get_settings
from atlas.services.llm.base import LLMProvider
from atlas.services.llm.gemini import GeminiProvider

_provider: LLMProvider | None = None


def build_llm(settings: Settings) -> LLMProvider:
    if os.environ.get("ATLAS_USE_FAKE_LLM") == "1":
        from atlas.services.llm.fake_provider import FakeLLM

        return FakeLLM()

    provider = settings.llm_provider
    if provider == "gemini":
        if not settings.gemini_api_key.strip():
            msg = "GEMINI_API_KEY is required when LLM_PROVIDER=gemini"
            raise ValueError(msg)
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            chat_model=settings.gemini_chat_model,
            embedding_model=settings.gemini_embedding_model,
            max_context=settings.gemini_max_context_tokens,
        )
    if provider == "claude":
        raise NotImplementedError("LLM_PROVIDER=claude is not implemented yet.")
    if provider == "openai":
        raise NotImplementedError("LLM_PROVIDER=openai is not implemented yet.")
    raise ValueError(f"Unknown LLM_PROVIDER={provider!r}")


def init_llm(settings: Settings | None = None) -> LLMProvider:
    global _provider
    cfg = settings or get_settings()
    _provider = build_llm(cfg)
    return _provider


def get_llm() -> LLMProvider:
    if _provider is None:
        msg = "LLM provider is not initialized (call init_llm during application startup)."
        raise RuntimeError(msg)
    return _provider


def reset_llm_for_tests() -> None:
    global _provider
    _provider = None


__all__ = [
    "GeminiProvider",
    "LLMProvider",
    "build_llm",
    "get_llm",
    "init_llm",
    "reset_llm_for_tests",
]
