from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.api.deps import get_db
from atlas.api.schemas.chat import ChatRequest
from atlas.config import get_settings
from atlas.services.chat_service import run_json_chat, stream_chat_sse
from atlas.services.llm import get_llm
from atlas.services.llm.base import LLMProvider

router = APIRouter(prefix="/chat", tags=["chat"])


async def _llm_dep() -> LLMProvider:
    return get_llm()


@router.post("", summary="Send a chat message (SSE or JSON)")
async def post_chat(
    body: ChatRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    llm: Annotated[LLMProvider, Depends(_llm_dep)],
) -> StreamingResponse | JSONResponse:
    settings = get_settings()

    if body.stream:

        async def event_stream():
            async for chunk in stream_chat_sse(
                session,
                llm,
                conversation_id=body.conversation_id,
                user_text=body.message,
                max_context_tokens=settings.gemini_max_context_tokens,
            ):
                yield chunk

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        payload = await run_json_chat(
            session,
            llm,
            conversation_id=body.conversation_id,
            user_text=body.message,
            max_context_tokens=settings.gemini_max_context_tokens,
        )
    except ValueError as exc:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})
    return JSONResponse(payload)
