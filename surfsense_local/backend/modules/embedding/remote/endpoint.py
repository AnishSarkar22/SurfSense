"""Where a remote embedder is called: its connection's URL and key, read fresh.

Read when the active index is, so editing the key or the URL keeps the index;
the spec names the connection, never its address.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from modules.egress import service as egress
from modules.embedding.spec import EmbedderSpec
from modules.llm.models import ProviderConnection


@dataclass(frozen=True)
class RemoteEndpoint:
    base_url: str
    api_key: str | None


class EmbeddingServerGoneError(Exception):
    """The connection an index embeds through no longer exists."""


def endpoint_for(session: Session, spec: EmbedderSpec) -> RemoteEndpoint:
    """The connection's address, once egress to its host is allowed."""
    connection = session.get(ProviderConnection, spec.connection_id)
    if connection is None:
        raise EmbeddingServerGoneError(
            f"the server {spec.model} is embedded through was removed"
        )
    egress.require(session, egress.host_destination(connection.base_url))
    return RemoteEndpoint(connection.base_url, connection.api_key)
