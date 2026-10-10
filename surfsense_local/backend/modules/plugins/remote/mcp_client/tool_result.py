"""What a `tools/call` returned: its text for a model, its data, and whether the tool failed."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    text: str
    content: list[dict[str, Any]]
    structured: dict[str, Any] | None
    # The tool ran and reported failure; the call itself succeeded.
    is_error: bool

    @classmethod
    def from_reply(cls, reply: dict[str, Any]) -> "ToolResult":
        content = reply.get("content") or []
        text = "\n".join(
            block["text"] for block in content if block.get("type") == "text"
        )
        return cls(
            text=text,
            content=content,
            structured=reply.get("structuredContent"),
            is_error=bool(reply.get("isError")),
        )
