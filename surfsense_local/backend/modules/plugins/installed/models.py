import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base, text_enum
from shared.secrets import decrypt, encrypt


class PluginKind(enum.StrEnum):
    REMOTE = "remote"


class PluginSource(enum.StrEnum):
    BUILT_IN = "built_in"
    REGISTRY = "registry"
    CUSTOM = "custom"


class ToolApproval(enum.StrEnum):
    ASK = "ask"
    ALWAYS = "always"


class ToolExposure(enum.StrEnum):
    DIRECT = "direct"
    DEFERRED = "deferred"


class InstalledPlugin(Base):
    """A plugin the user connected, and the list entry it was connected from."""

    __tablename__ = "installed_plugins"

    id: Mapped[str] = mapped_column(primary_key=True)
    kind: Mapped[PluginKind] = mapped_column(text_enum(PluginKind))
    source: Mapped[PluginSource] = mapped_column(text_enum(PluginSource))
    url: Mapped[str]
    publisher: Mapped[str]
    # The entry as listed at connect: name, auth, hosts, access. Kept so a plugin whose
    # entry later leaves its list still shows what it was.
    entry: Mapped[dict[str, Any]] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(default=True)
    connected_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PluginCredential(Base):
    """A plugin's sign-in, encrypted; never shown to a model, a log or a step."""

    __tablename__ = "plugin_credentials"

    plugin_id: Mapped[str] = mapped_column(
        ForeignKey("installed_plugins.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str]
    ciphertext: Mapped[bytes]

    @property
    def token(self) -> str:
        return decrypt(self.ciphertext)

    @token.setter
    def token(self, value: str) -> None:
        self.ciphertext = encrypt(value)


class PluginTool(Base):
    """A tool a connected plugin offers, its switches, and how it last described itself."""

    __tablename__ = "plugin_tools"

    plugin_id: Mapped[str] = mapped_column(
        ForeignKey("installed_plugins.id", ondelete="CASCADE"), primary_key=True
    )
    tool: Mapped[str] = mapped_column(primary_key=True)
    # Where the server listed it, so tools keep the order their publisher chose.
    position: Mapped[int]
    title: Mapped[str | None]
    description: Mapped[str]
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON)
    annotations: Mapped[dict[str, Any]] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(default=True)
    approval: Mapped[ToolApproval] = mapped_column(
        text_enum(ToolApproval), default=ToolApproval.ASK
    )
    exposure: Mapped[ToolExposure] = mapped_column(
        text_enum(ToolExposure), default=ToolExposure.DIRECT
    )
    first_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PluginSettings(Base):
    """One row: whether other publishers' plugins are on (Restricted mode off)."""

    __tablename__ = "plugin_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    other_publishers_on: Mapped[bool] = mapped_column(default=False)
