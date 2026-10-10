"""`list_tools`: the tools ready to be called, from what connected plugins recorded."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.plugins.gateway.qualified_name import qualified_name
from modules.plugins.gateway.ready_tool import ReadyTool
from modules.plugins.installed.models import InstalledPlugin, PluginTool
from modules.plugins.installed.other_publishers import other_publishers_on
from modules.plugins.installed.plugin_hosts import hosts_not_allowed

SURFSENSE = "surfsense"


def list_tools(session: Session) -> list[ReadyTool]:
    others_on = other_publishers_on(session)
    ready: dict[str, bool] = {}

    def is_ready(plugin: InstalledPlugin) -> bool:
        if plugin.id not in ready:
            ready[plugin.id] = (
                others_on or plugin.publisher == SURFSENSE
            ) and not hosts_not_allowed(session, plugin)
        return ready[plugin.id]

    rows = session.execute(
        select(InstalledPlugin, PluginTool)
        .join(PluginTool, PluginTool.plugin_id == InstalledPlugin.id)
        .where(InstalledPlugin.enabled, PluginTool.enabled)
        .order_by(InstalledPlugin.connected_at, InstalledPlugin.id, PluginTool.position)
    )
    taken: set[str] = set()

    def distinct_name(plugin_id: str, tool: str) -> str:
        name = qualified_name(plugin_id, tool, taken=taken)
        taken.add(name)
        return name

    # The first plugin connected keeps the plain name; a later one that collides is hashed.
    return [
        ReadyTool(
            qualified_name=distinct_name(plugin.id, row.tool),
            plugin_id=plugin.id,
            plugin_name=plugin.entry.get("name", plugin.id),
            plugin_source=plugin.source,
            tool=row.tool,
            title=row.title,
            description=row.description,
            input_schema=row.input_schema,
            annotations=row.annotations,
            approval=row.approval,
            exposure=row.exposure,
        )
        for plugin, row in rows
        if is_ready(plugin)
    ]
