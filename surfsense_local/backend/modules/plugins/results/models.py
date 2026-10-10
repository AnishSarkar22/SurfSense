import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base, text_enum


class PluginCaller(enum.StrEnum):
    AGENT = "agent"
    CHAT_ROUTER = "chat_router"
    MENTION = "mention"


class PluginCallStatus(enum.StrEnum):
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    CANCELLED = "cancelled"


class PluginCall(Base):
    """One call of a plugin's tool, its arguments, and its whole result.

    `plugin_id` is no foreign key: a past call stays in its thread after the plugin is
    disconnected. The thread is either kind, agent or chat, so it is a bare id too.
    """

    __tablename__ = "plugin_calls"
    __table_args__ = (Index("plugin_calls_plugin", "plugin_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    thread_id: Mapped[int | None]
    message_id: Mapped[int | None]
    caller: Mapped[PluginCaller] = mapped_column(text_enum(PluginCaller))
    plugin_id: Mapped[str]
    tool: Mapped[str]
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[PluginCallStatus] = mapped_column(text_enum(PluginCallStatus))
    # Whole, never trimmed: the step shows all of it; a model gets it trimmed.
    result_text: Mapped[str | None]
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None]
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None]
