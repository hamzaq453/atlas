from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from atlas.db.session import get_session_factory
from atlas.services.llm import get_llm
from atlas.services.llm.base import LLMProvider


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def get_llm_dep() -> LLMProvider:
    return get_llm()
