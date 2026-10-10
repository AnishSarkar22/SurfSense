"""`call_tool`: the only door to a plugin's tool, for every caller."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from modules.plugins.gateway.approval import Approve, needs_approval
from modules.plugins.gateway.argument_check import argument_problem
from modules.plugins.gateway.listing import list_tools
from modules.plugins.gateway.scope import Scope
from modules.plugins.gateway.tool_outcome import ToolOutcome
from modules.plugins.gateway.tool_source import ToolSource
from modules.plugins.gateway.trimming import trimmed_for_model
from modules.plugins.installed.models import InstalledPlugin
from modules.plugins.results.models import PluginCall, PluginCaller, PluginCallStatus

SourceFor = Callable[[InstalledPlugin], ToolSource]


async def call_tool(
    session: Session,
    scope: Scope,
    qualified_name: str,
    arguments: dict[str, Any],
    *,
    caller: PluginCaller,
    source_for: SourceFor,
    approve: Approve,
) -> ToolOutcome:
    ready = {tool.qualified_name: tool for tool in list_tools(session)}
    tool = ready.get(qualified_name)
    if tool is None:
        return ToolOutcome(
            PluginCallStatus.FAILED,
            f"{qualified_name} is not available: it is unknown, switched off, "
            "or its plugin is not connected.",
        )
    problem = argument_problem(tool.input_schema, arguments)
    if problem is not None:
        return ToolOutcome(
            PluginCallStatus.FAILED, f"{qualified_name} was not called. {problem}"
        )
    asking = needs_approval(tool)
    call = PluginCall(
        workspace_id=scope.workspace_id,
        thread_id=scope.thread_id,
        message_id=scope.message_id,
        caller=caller,
        plugin_id=tool.plugin_id,
        tool=tool.tool,
        arguments=arguments,
        status=PluginCallStatus.WAITING_APPROVAL
        if asking
        else PluginCallStatus.RUNNING,
    )
    session.add(call)
    session.commit()
    if asking:
        if not await approve(tool, arguments):
            call.status = PluginCallStatus.DENIED
            call.finished_at = datetime.now(UTC)
            session.commit()
            return ToolOutcome(
                call.status, "The user did not allow this call.", call_id=call.id
            )
        call.status = PluginCallStatus.RUNNING
        session.commit()

    plugin = session.get_one(InstalledPlugin, tool.plugin_id)
    try:
        result = await source_for(plugin).call_tool(tool.tool, arguments)
    # Any source's failure ends this call, never the turn that made it.
    except Exception as error:
        call.status = PluginCallStatus.FAILED
        call.error = str(error)
        call.finished_at = datetime.now(UTC)
        session.commit()
        return ToolOutcome(
            call.status, f"{qualified_name} failed: {error}", call_id=call.id
        )
    call.status = PluginCallStatus.SUCCEEDED
    call.result_text = result.text
    call.result_data = result.structured
    call.finished_at = datetime.now(UTC)
    session.commit()
    return ToolOutcome(
        call.status, trimmed_for_model(result.text), result.structured, call.id
    )
