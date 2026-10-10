"""Every host a plugin contacts, and whether the user allowed all of them."""

from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from modules.egress.models import EgressDestination
from modules.egress.service import host_destination
from modules.plugins.installed.models import InstalledPlugin


def plugin_hosts(plugin: InstalledPlugin) -> list[str]:
    """The URL's host first, then the hosts its entry declares, each once."""
    hosts = [urlsplit(plugin.url).hostname or "", *plugin.entry.get("hosts", [])]
    return list(dict.fromkeys(host for host in hosts if host))


def hosts_not_allowed(session: Session, plugin: InstalledPlugin) -> list[str]:
    """Hosts still to allow; loopback never needs consent, since nothing leaves the machine."""
    missing = []
    for host in plugin_hosts(plugin):
        destination = host_destination(f"https://{host}")
        if destination is None:
            continue
        row = session.get(EgressDestination, destination)
        if row is None or not row.enabled:
            missing.append(host)
    return missing
