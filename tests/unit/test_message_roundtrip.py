from __future__ import annotations

from atlas.services.llm.types import Message, ToolCall


def test_message_tool_calls_roundtrip_json() -> None:
    msg = Message(
        role="assistant",
        content="ok",
        tool_calls=[ToolCall(name="demo", arguments={"x": 1})],
    )
    dumped = msg.model_dump()
    restored = Message.model_validate(dumped)
    assert restored.tool_calls is not None
    assert restored.tool_calls[0].name == "demo"
    assert restored.tool_calls[0].arguments == {"x": 1}
