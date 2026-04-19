from __future__ import annotations

from atlas.services.llm.types import Message


def approximate_token_count(text: str) -> int:
    """Rough Gemini-oriented estimate: ~4 characters per token."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def approximate_messages_token_count(messages: list[Message]) -> int:
    total = 0
    for msg in messages:
        total += approximate_token_count(msg.content)
        if msg.tool_calls:
            for tc in msg.tool_calls:
                total += approximate_token_count(tc.name)
                total += approximate_token_count(str(tc.arguments))
    return total


def truncate_messages_to_token_budget(
    messages: list[Message],
    *,
    max_tokens: int,
    reserve_for_reply: int = 1024,
) -> list[Message]:
    """Drop oldest non-system messages until under the token budget."""
    budget = max_tokens - reserve_for_reply
    if budget <= 0:
        return list(messages)

    system_msgs = [m for m in messages if m.role == "system"]
    rest = [m for m in messages if m.role != "system"]

    trimmed: list[Message] = list(rest)
    while trimmed and approximate_messages_token_count(system_msgs + trimmed) > budget:
        trimmed.pop(0)

    return system_msgs + trimmed
