"""`RemoteMcpSource`: a remote plugin's MCP server, as the gateway's `ToolSource`."""

from typing import Any

from modules.plugins.gateway.source_result import SourceResult
from modules.plugins.gateway.source_tool import SourceTool
from modules.plugins.remote.mcp_client.progress import OnProgress
from modules.plugins.remote.mcp_client.session import McpSession


class RemoteMcpSource:
    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self._session = McpSession(url, headers)

    async def list_tools(self) -> list[SourceTool]:
        return [
            SourceTool(
                name=tool.name,
                title=tool.title,
                description=tool.description,
                input_schema=tool.input_schema,
                annotations=tool.annotations,
            )
            for tool in await self._session.list_tools()
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        timeout: float | None = None,
        on_progress: OnProgress | None = None,
    ) -> SourceResult:
        result = await self._session.call_tool(
            name, arguments, timeout=timeout, on_progress=on_progress
        )
        return SourceResult(
            text=result.text, structured=result.structured, is_error=result.is_error
        )

    async def close(self) -> None:
        await self._session.close()
