from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ChatRole = Literal["system", "user", "assistant", "tool"]


class ToolCall(BaseModel):
    """Serialized tool invocation (provider-agnostic)."""

    id: str | None = None
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    role: ChatRole
    content: str = ""
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class LLMResponse(BaseModel):
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: dict[str, Any] | None = None


class LLMChunk(BaseModel):
    delta: str = ""
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
