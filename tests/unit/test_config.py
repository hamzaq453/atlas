from __future__ import annotations

from atlas.config import Settings


def test_settings_loads_required_urls() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://atlas:atlas_dev@localhost:5432/atlas_dev",
        test_database_url="postgresql+asyncpg://atlas:atlas_dev@localhost:5432/atlas_test",
        llm_provider="groq",
    )

    assert "atlas_dev" in settings.database_url
    assert "atlas_test" in settings.test_database_url
    assert settings.llm_provider == "groq"
    assert settings.env == "local"
    assert settings.timezone == "Asia/Karachi"


def test_settings_defaults_test_database_url_when_empty() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://atlas:atlas_dev@localhost:5432/atlas_dev",
        test_database_url="",
    )

    assert settings.test_database_url == settings.database_url


def test_settings_normalizes_plain_postgresql_scheme() -> None:
    settings = Settings(
        database_url="postgresql://atlas:atlas_dev@localhost:5432/atlas_dev",
        test_database_url="",
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.test_database_url == settings.database_url
