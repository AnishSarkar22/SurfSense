"""A plugin's MCP server, reached through the official SDK's client over Streamable HTTP.

Each operation opens its own SDK client: the SDK's tasks must close in the task that
opened them, and a request handler cannot promise that across calls.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx2
from mcp.client.client import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError

from modules.plugins.remote.mcp_client.http_failure import unreachable
from modules.plugins.remote.mcp_client.progress import OnProgress, Progress
from modules.plugins.remote.mcp_client.remote_tool import RemoteTool
from modules.plugins.remote.mcp_client.retries import retried
from modules.plugins.remote.mcp_client.sdk_errors import translated
from modules.plugins.remote.mcp_client.session_expired import SessionExpiredError
from modules.plugins.remote.mcp_client.tool_result import ToolResult
from modules.plugins.remote.mcp_client.unwrapped import unwrapped


class McpSession:
    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self._url = url
        self._headers = headers or {}

    async def list_tools(self) -> list[RemoteTool]:
        return await retried(
            lambda: self._in_fresh_session(self._list_every_page, "listing")
        )

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        on_progress: OnProgress | None = None,
        timeout: float | None = None,
    ) -> ToolResult:
        async def report(
            progress: float, total: float | None, message: str | None
        ) -> None:
            if on_progress is not None:
                on_progress(Progress(progress=progress, total=total, message=message))

        async def call(client: Client) -> ToolResult:
            result = await client.call_tool(
                name, arguments, read_timeout_seconds=timeout, progress_callback=report
            )
            return ToolResult.from_reply(
                result.model_dump(by_alias=True, exclude_none=True)
            )

        return await self._in_fresh_session(call, name)

    async def close(self) -> None:
        """Nothing stays open between operations."""

    async def _list_every_page(self, client: Client) -> list[RemoteTool]:
        tools: list[RemoteTool] = []
        cursor: str | None = None
        while True:
            page = await client.list_tools(cursor=cursor, cache_mode="bypass")
            tools += [
                RemoteTool.from_listing(
                    tool.model_dump(by_alias=True, exclude_none=True)
                )
                for tool in page.tools
            ]
            cursor = page.next_cursor
            if not cursor:
                return tools

    async def _in_fresh_session[T](
        self, operation: Callable[[Client], Awaitable[T]], what: str
    ) -> T:
        """Run once more on a new session if the server forgot ours: it handled nothing."""
        try:
            return await self._run(operation, what)
        except SessionExpiredError:
            return await self._run(operation, what)

    async def _run[T](
        self, operation: Callable[[Client], Awaitable[T]], what: str
    ) -> T:
        failed_status: list[int] = []

        async def record_failure(response: httpx2.Response) -> None:
            if response.status_code >= 400:
                failed_status.append(response.status_code)

        try:
            async with self._client(record_failure) as client:
                return await operation(client)
        except (MCPError, httpx2.TransportError, BaseExceptionGroup) as raised:
            error = unwrapped(raised)
            if isinstance(error, MCPError):
                status = failed_status[-1] if failed_status else None
                raise translated(error, status, what) from error
            if isinstance(error, httpx2.TransportError):
                raise unreachable(error) from error
            raise

    @asynccontextmanager
    async def _client(
        self, on_response: Callable[[httpx2.Response], Awaitable[None]]
    ) -> AsyncIterator[Client]:
        async with (
            httpx2.AsyncClient(
                headers=self._headers, event_hooks={"response": [on_response]}
            ) as http,
            Client(streamable_http_client(self._url, http_client=http)) as client,
        ):
            yield client
