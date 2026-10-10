"""Restricted mode: whether the user turned other publishers' plugins on."""

from sqlalchemy.orm import Session

from modules.plugins.installed.models import PluginSettings

SETTINGS_ROW = 1


def other_publishers_on(session: Session) -> bool:
    settings = session.get(PluginSettings, SETTINGS_ROW)
    return settings is not None and settings.other_publishers_on
