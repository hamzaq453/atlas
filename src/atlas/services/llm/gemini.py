from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any, cast

import google.generativeai as genai

from atlas.services.llm.types import LLMChunk, LLMResponse, Message, ToolCall

_SENTINEL = object()


def _split_system_and_contents(
    messages: list[Message],
) -> tuple[str | None, list[dict[str, Any]]]:
    system_chunks: list[str] = []
    contents: list[dict[str, Any]] = []

    for msg in messages:
        if msg.role == "system":
            system_chunks.append(msg.content)
            continue

        role = "model" if msg.role == "assistant" else "user"
        parts: list[dict[str, Any]] = []

        if msg.role == "tool":
            label = msg.tool_call_id or "tool"
            parts.append({"text": f"[tool result {label}]\n{msg.content}"})
        else:
            if msg.content:
                parts.append({"text": msg.content})
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    parts.append(
                        {
                            "function_call": {
                                "name": tc.name,
                                "args": tc.arguments,
                            },
                        },
                    )

        if not parts:
            parts.append({"text": ""})

        contents.append({"role": role, "parts": parts})

    system_instruction = "\n\n".join(system_chunks).strip() or None
    return system_instruction, contents


def _extract_text_from_candidate(candidate: Any) -> str:
    parts_out: list[str] = []
    content = getattr(candidate, "content", None)
    if content is None:
        return ""
    for part in getattr(content, "parts", []) or []:
        text = getattr(part, "text", None)
        if text:
            parts_out.append(text)
        fc = getattr(part, "function_call", None)
        if fc is not None:
            name = getattr(fc, "name", "function")
            args = dict(getattr(fc, "args", {}) or {})
            parts_out.append(f"\n[{name}({json.dumps(args)})]\n")
    return "".join(parts_out).strip()


def _extract_tool_calls_from_candidate(candidate: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    content = getattr(candidate, "content", None)
    if content is None:
        return calls
    for part in getattr(content, "parts", []) or []:
        fc = getattr(part, "function_call", None)
        if fc is None:
            continue
        name = getattr(fc, "name", "")
        args = dict(getattr(fc, "args", {}) or {})
        calls.append(ToolCall(name=name, arguments=args))
    return calls


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        chat_model: str,
        embedding_model: str,
        max_context: int = 1_048_576,
    ) -> None:
        genai.configure(api_key=api_key)
        self.model = chat_model
        self._embedding_model = embedding_model
        self.max_context: int = max_context

    async def complete(self, messages: list[Message], **opts: Any) -> LLMResponse:
        system_instruction, contents = _split_system_and_contents(messages)
        generation_config = opts.get("generation_config")

        def _run() -> LLMResponse:
            model = genai.GenerativeModel(
                self.model,
                system_instruction=system_instruction,
            )
            response = model.generate_content(
                contents,
                stream=False,
                generation_config=generation_config,
            )
            text = (getattr(response, "text", None) or "").strip()
            tool_calls: list[ToolCall] = []
            finish_reason: str | None = None
            for cand in getattr(response, "candidates", []) or []:
                text = text or _extract_text_from_candidate(cand)
                tool_calls.extend(_extract_tool_calls_from_candidate(cand))
                fr = getattr(getattr(cand, "finish_reason", None), "name", None)
                if isinstance(fr, str):
                    finish_reason = fr
            usage: dict[str, Any] | None = None
            um = getattr(response, "usage_metadata", None)
            if um is not None:
                usage = {
                    "prompt_token_count": getattr(um, "prompt_token_count", None),
                    "candidates_token_count": getattr(um, "candidates_token_count", None),
                    "total_token_count": getattr(um, "total_token_count", None),
                }
            return LLMResponse(
                content=text,
                tool_calls=tool_calls,
                usage=usage,
            )

        return await asyncio.to_thread(_run)

    async def stream(self, messages: list[Message], **opts: Any) -> AsyncIterator[LLMChunk]:
        system_instruction, contents = _split_system_and_contents(messages)
        generation_config = opts.get("generation_config")

        def _build_iterator() -> Any:
            model = genai.GenerativeModel(
                self.model,
                system_instruction=system_instruction,
            )
            return iter(model.generate_content(contents, stream=True, generation_config=generation_config))

        iterator = await asyncio.to_thread(_build_iterator)

        def _next_chunk() -> LLMChunk | object:
            try:
                return next(iterator)
            except StopIteration:
                return _SENTINEL
            text = getattr(chunk, "text", "") or ""
            finish = None
            for cand in getattr(chunk, "candidates", []) or []:
                fr = getattr(getattr(cand, "finish_reason", None), "name", None)
                if isinstance(fr, str):
                    finish = fr
            usage = None
            um = getattr(chunk, "usage_metadata", None)
            if um is not None:
                usage = {
                    "prompt_token_count": getattr(um, "prompt_token_count", None),
                    "candidates_token_count": getattr(um, "candidates_token_count", None),
                    "total_token_count": getattr(um, "total_token_count", None),
                }
            return LLMChunk(delta=text, finish_reason=finish, usage=usage)

        while True:
            item = await asyncio.to_thread(_next_chunk)
            if item is _SENTINEL:
                break
            yield cast(LLMChunk, item)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []

        def _embed_one(text: str) -> list[float]:
            result = genai.embed_content(
                model=self._embedding_model,
                content=text,
                task_type="retrieval_document",
            )
            emb = result.get("embedding")
            if not isinstance(emb, list):
                raise TypeError("Unexpected embedding response from Gemini")
            return [float(x) for x in emb]

        for text in texts:
            vectors.append(await asyncio.to_thread(_embed_one, text))
        return vectors
