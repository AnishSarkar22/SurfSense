"""Anything that can list and call tools: a remote server now, a bundle's process later.

Nothing above the gateway knows which kind a tool came from.
"""

from typing import Any, Protocol

from modules.plugins.gateway.source_result import SourceResult
from modules.plugins.gateway.source_tool import SourceTool


class ToolSource(Protocol):
    async def list_tools(self) -> list[SourceTool]: ...

    async def call_tool(
        self, name: str, arguments: dict[str, Any], *, timeout: float | None = None
    ) -> SourceResult: ...
