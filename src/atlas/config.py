from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Application configuration loaded from environment and optional `.env` file."""

    model_config = SettingsConfigDict(
        env_file=_DOTENV_PATH if _DOTENV_PATH.is_file() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="Async SQLAlchemy URL for the primary dev/prod database.",
    )
    test_database_url: str = Field(
        default="",
        description="Async URL for pytest; defaults to DATABASE_URL when empty.",
    )
    gemini_api_key: str = Field(default="", description="Google Gemini API key (Phase 2+).")
    gemini_chat_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model id for chat completions.",
    )
    gemini_embedding_model: str = Field(
        default="models/text-embedding-004",
        description="Gemini embedding model id.",
    )
    gemini_max_context_tokens: int = Field(
        default=1_048_576,
        description="Approximate max context window for truncation heuristics.",
    )
    groq_api_key: str = Field(default="", description="Groq API key when LLM_PROVIDER=groq.")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq OpenAI-compatible base URL.",
    )
    groq_chat_model: str = Field(
        default="qwen/qwen3-32b",
        description="Groq chat model id.",
    )

    llm_provider: Literal["gemini", "groq", "claude", "openai"] = Field(
        default="groq",
        description="LLM provider id (Phase 2+).",
    )
    log_level: str = Field(default="INFO")
    env: Literal["local", "prod"] = Field(default="local")
    timezone: str = Field(default="Asia/Karachi")
    atlas_admin_database_url: str | None = Field(
        default=None,
        description="Superuser async URL used only by scripts/reset_db.py (database=postgres).",
    )

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def normalize_asyncpg_scheme(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgres://")
        return value

    @field_validator("atlas_admin_database_url", mode="before")
    @classmethod
    def empty_admin_url_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def default_test_database_url(self) -> Self:
        if not self.test_database_url.strip():
            self.test_database_url = self.database_url
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Values are sourced from environment / `.env` at runtime.
    return Settings()  # type: ignore[call-arg]
