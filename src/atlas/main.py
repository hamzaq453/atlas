from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas.api.routes import chat, conversations, health
from atlas.config import get_settings
from atlas.logging import setup_logging
from atlas.services.llm import init_llm, reset_llm_for_tests


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(json_logs=settings.env == "prod", log_level=settings.log_level)
    init_llm(settings)
    yield
    reset_llm_for_tests()


def create_app() -> FastAPI:
    app = FastAPI(title="Atlas", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    return app


app = create_app()
