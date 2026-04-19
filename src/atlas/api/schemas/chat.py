from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str = Field(..., min_length=1, max_length=32_000)
    stream: bool = True
