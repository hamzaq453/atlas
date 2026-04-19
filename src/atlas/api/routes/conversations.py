from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.api.deps import get_db
from atlas.models.conversation import Conversation, ConversationMessage

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationSummary(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str


class ConversationMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    tool_calls_json: str | None
    created_at: str


@router.get("", summary="List recent conversations")
async def list_conversations(
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
) -> list[ConversationSummary]:
    stmt = (
        select(Conversation).order_by(Conversation.updated_at.desc()).limit(min(max(limit, 1), 200))
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    return [
        ConversationSummary(
            id=row.id,
            user_id=row.user_id,
            title=row.title,
        )
        for row in rows
    ]


@router.get("/{conversation_id}/messages", summary="Fetch ordered message history")
async def list_messages(
    conversation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ConversationMessageOut]:
    conv = await session.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    return [
        ConversationMessageOut(
            id=row.id,
            role=row.role,
            content=row.content,
            tool_calls_json=row.tool_calls_json,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
