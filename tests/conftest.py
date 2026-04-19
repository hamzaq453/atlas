from __future__ import annotations

import os
from collections.abc import AsyncIterator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

# Load `.env` from the repo root so pytest picks up DATABASE_URL even when cwd differs.
# `override=True` ensures repo `.env` wins over a stale machine-level DATABASE_URL.
_REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_REPO_ROOT / ".env", override=True)

_test_url = (
    os.environ.get("TEST_DATABASE_URL", "").strip()
    or os.environ.get("DATABASE_URL", "").strip()
    or "postgresql+asyncpg://atlas:atlas_dev@localhost:5432/atlas_test"
)
os.environ["DATABASE_URL"] = _test_url
os.environ["TEST_DATABASE_URL"] = _test_url
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("ENV", "local")
os.environ.setdefault("LOG_LEVEL", "INFO")

from atlas.config import get_settings
from atlas.db import session as session_module
from atlas.main import app


@pytest.fixture(autouse=True)
def _reset_app_state() -> Generator[None, None, None]:
    get_settings.cache_clear()
    session_module._engine = None
    session_module._session_factory = None
    yield
    get_settings.cache_clear()
    session_module._engine = None
    session_module._session_factory = None


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
