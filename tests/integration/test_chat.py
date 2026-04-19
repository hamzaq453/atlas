from __future__ import annotations

import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_chat_sse_persists_messages(client: AsyncClient) -> None:
    async with client.stream(
        "POST",
        "/chat",
        json={"message": "hello from tests", "stream": True},
    ) as response:
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")

        events: list[dict[str, object]] = []
        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = json.loads(line.removeprefix("data:").strip())
            events.append(payload)

    types = [e.get("type") for e in events]
    assert "token" in types
    assert "done" in types

    done = next(e for e in events if e.get("type") == "done")
    conversation_id = str(done["conversation_id"])

    history = await client.get(f"/conversations/{conversation_id}/messages")
    assert history.status_code == 200
    body = history.json()
    assert len(body) >= 2
    assert body[0]["role"] == "user"
    assert "hello from tests" in body[0]["content"]
    assert body[-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_post_chat_json_mode(client: AsyncClient) -> None:
    response = await client.post(
        "/chat",
        json={"message": "ping", "stream": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["content"].startswith("echo:ping")
    assert "conversation_id" in payload
    assert "message_id" in payload
