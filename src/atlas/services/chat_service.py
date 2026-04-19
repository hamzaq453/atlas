from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.models.conversation import Conversation, ConversationMessage
from atlas.services.llm.base import LLMProvider
from atlas.services.llm.tokens import approximate_messages_token_count, truncate_messages_to_token_budget
from atlas.services.llm.types import Message
from atlas.services.prompts.system import default_system_prompt


DEFAULT_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


def _title_from_message(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "New chat"
    return cleaned[:200]


async def get_or_create_conversation(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID | None,
    user_message: str,
) -> Conversation:
    now = datetime.now(timezone.utc)
    if conversation_id is not None:
        conv = await session.get(Conversation, conversation_id)
        if conv is None:
            msg = f"Conversation {conversation_id} not found"
            raise ValueError(msg)
        conv.updated_at = now
        return conv

    conv = Conversation(
        user_id=DEFAULT_USER_ID,
        title=_title_from_message(user_message),
        created_at=now,
        updated_at=now,
    )
    session.add(conv)
    await session.flush()
    return conv


def _rows_to_messages(rows: list[ConversationMessage]) -> list[Message]:
    messages: list[Message] = []
    for row in rows:
        tool_calls = None
        if row.tool_calls_json:
            try:
                raw = json.loads(row.tool_calls_json)
                if isinstance(raw, list):
                    from atlas.services.llm.types import ToolCall

                    tool_calls = [ToolCall.model_validate(item) for item in raw]
            except (json.JSONDecodeError, ValueError):
                tool_calls = None
        role = row.role
        if role not in ("system", "user", "assistant", "tool"):
            role = "user"
        messages.append(
            Message(
                role=role,  # type: ignore[arg-type]
                content=row.content,
                tool_calls=tool_calls,
            ),
        )
    return messages


async def build_llm_messages(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    max_context_tokens: int,
) -> list[Message]:
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc()),
    )
    rows = list(result.scalars().all())
    history = _rows_to_messages(rows)
    system = Message(role="system", content=default_system_prompt())
    combined = [system, *history]
    return truncate_messages_to_token_budget(
        combined,
        max_tokens=max_context_tokens,
        reserve_for_reply=2048,
    )


async def persist_message(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    tool_calls_json: str | None = None,
) -> ConversationMessage:
    now = datetime.now(timezone.utc)
    msg = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls_json=tool_calls_json,
        created_at=now,
    )
    session.add(msg)
    conv = await session.get(Conversation, conversation_id)
    if conv is not None:
        conv.updated_at = now
    await session.flush()
    return msg


async def stream_chat_sse(
    session: AsyncSession,
    llm: LLMProvider,
    *,
    conversation_id: uuid.UUID | None,
    user_text: str,
    max_context_tokens: int,
) -> AsyncIterator[str]:
    queue: asyncio.Queue[dict[str, object] | object] = asyncio.Queue()
    done = asyncio.Event()

    async def heartbeat() -> None:
        while not done.is_set():
            await asyncio.sleep(15)
            if done.is_set():
                return
            await queue.put({"type": "heartbeat"})

    async def producer() -> None:
        try:
            conv = await get_or_create_conversation(
                session,
                conversation_id=conversation_id,
                user_message=user_text,
            )
            await persist_message(
                session,
                conversation_id=conv.id,
                role="user",
                content=user_text,
            )
            await session.commit()

            await queue.put(
                {
                    "type": "meta",
                    "conversation_id": str(conv.id),
                },
            )

            messages = await build_llm_messages(
                session,
                conversation_id=conv.id,
                max_context_tokens=max_context_tokens,
            )
            # Ensure the latest user turn is included even if truncation dropped older rows.
            if not messages or messages[-1].role != "user" or messages[-1].content != user_text:
                messages.append(Message(role="user", content=user_text))

            assistant_parts: list[str] = []
            async for chunk in llm.stream(messages):
                assistant_parts.append(chunk.delta)
                await queue.put(
                    {
                        "type": "token",
                        "data": chunk.delta,
                    },
                )

            assistant_text = "".join(assistant_parts).strip()
            saved = await persist_message(
                session,
                conversation_id=conv.id,
                role="assistant",
                content=assistant_text,
            )
            await session.commit()

            await queue.put(
                {
                    "type": "done",
                    "conversation_id": str(conv.id),
                    "message_id": str(saved.id),
                },
            )
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(_SENTINEL_END)


_SENTINEL_END = object()


async def run_json_chat(
    session: AsyncSession,
    llm: LLMProvider,
    *,
    conversation_id: uuid.UUID | None,
    user_text: str,
    max_context_tokens: int,
) -> dict[str, object]:
    conv = await get_or_create_conversation(
        session,
        conversation_id=conversation_id,
        user_message=user_text,
    )
    await persist_message(session, conversation_id=conv.id, role="user", content=user_text)
    await session.commit()

    messages = await build_llm_messages(
        session,
        conversation_id=conv.id,
        max_context_tokens=max_context_tokens,
    )
    if not messages or messages[-1].role != "user" or messages[-1].content != user_text:
        messages.append(Message(role="user", content=user_text))

    if approximate_messages_token_count(messages) > max_context_tokens:
        messages = truncate_messages_to_token_budget(
            messages,
            max_tokens=max_context_tokens,
            reserve_for_reply=2048,
        )

    response = await llm.complete(messages)
    saved = await persist_message(
        session,
        conversation_id=conv.id,
        role="assistant",
        content=response.content,
        tool_calls_json=json.dumps([tc.model_dump() for tc in response.tool_calls])
        if response.tool_calls
        else None,
    )
    await session.commit()

    return {
        "conversation_id": str(conv.id),
        "message_id": str(saved.id),
        "content": response.content,
        "tool_calls": [tc.model_dump() for tc in response.tool_calls],
        "usage": response.usage,
    }
