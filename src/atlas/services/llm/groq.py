from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, cast

from openai import AsyncOpenAI

from atlas.services.llm.base import LLMProvider
from atlas.services.llm.types import LLMChunk, LLMResponse, Message, ToolCall


def _messages_to_openai(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == "tool":
            label = msg.tool_call_id or "tool"
            out.append({"role": "user", "content": f"[tool result {label}]\n{msg.content}"})
            continue

        if msg.role == "assistant" and msg.tool_calls:
            tool_calls_payload = []
            for tc in msg.tool_calls:
                tool_calls_payload.append(
                    {
                        "id": tc.id or f"call_{tc.name}",
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    },
                )
            entry: dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or None,
                "tool_calls": tool_calls_payload,
            }
            out.append(entry)
            continue

        out.append({"role": msg.role, "content": msg.content})
    return out


class GroqProvider(LLMProvider):
    """Groq-hosted models via the OpenAI-compatible HTTP API."""

    name = "groq"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.groq.com/openai/v1",
        max_context: int = 131_072,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_context = max_context

    async def complete(self, messages: list[Message], **opts: Any) -> LLMResponse:
        openai_messages = _messages_to_openai(messages)
        extra: dict[str, Any] = {}
        if "temperature" in opts:
            extra["temperature"] = opts["temperature"]

        response = cast(
            Any,
            await self._client.chat.completions.create(
                model=self.model,
                messages=cast(Any, openai_messages),
                stream=False,
                **extra,
            ),
        )
        assistant_message = response.choices[0].message
        content = (assistant_message.content or "").strip()
        tool_calls: list[ToolCall] = []
        raw_tool_calls = getattr(assistant_message, "tool_calls", None)
        if raw_tool_calls:
            for tc in raw_tool_calls:
                args: dict[str, Any] = {}
                if tc.function.arguments:
                    try:
                        parsed = json.loads(tc.function.arguments)
                        if isinstance(parsed, dict):
                            args = parsed
                    except json.JSONDecodeError:
                        args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args),
                )

        usage: dict[str, Any] | None = None
        usage_obj = getattr(response, "usage", None)
        if usage_obj is not None:
            usage = {
                "prompt_tokens": usage_obj.prompt_tokens,
                "completion_tokens": usage_obj.completion_tokens,
                "total_tokens": usage_obj.total_tokens,
            }

        return LLMResponse(content=content, tool_calls=tool_calls, usage=usage)

    async def stream(self, messages: list[Message], **opts: Any) -> AsyncIterator[LLMChunk]:
        openai_messages = _messages_to_openai(messages)
        extra: dict[str, Any] = {}
        if "temperature" in opts:
            extra["temperature"] = opts["temperature"]

        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=cast(Any, openai_messages),
            stream=True,
            **extra,
        )

        async for chunk in cast(Any, stream):
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = delta.content or ""
            finish = None
            if chunk.choices[0].finish_reason:
                finish = str(chunk.choices[0].finish_reason)
            usage = None
            usage_obj = getattr(chunk, "usage", None)
            if usage_obj is not None:
                usage = {
                    "prompt_tokens": usage_obj.prompt_tokens,
                    "completion_tokens": usage_obj.completion_tokens,
                    "total_tokens": usage_obj.total_tokens,
                }
            if text or finish or usage:
                yield LLMChunk(delta=text, finish_reason=finish, usage=usage)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        msg = (
            "GroqProvider does not implement embeddings yet. "
            "Use LLM_PROVIDER=gemini for embedding-only flows, or add a dedicated embed provider."
        )
        raise NotImplementedError(msg)
