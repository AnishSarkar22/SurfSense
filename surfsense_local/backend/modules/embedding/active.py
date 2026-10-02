from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.embedding.models import EmbeddingIndex, IndexState
from modules.embedding.remote.endpoint import RemoteEndpoint, endpoint_for
from modules.embedding.spec import EmbedderSpec, Source


class EmbeddingNotChosenError(Exception):
    """Nothing may be embedded before onboarding fixes the model."""

    def __init__(self) -> None:
        super().__init__("no embedding model has been chosen yet")


@dataclass(frozen=True)
class ActiveIndex:
    id: int
    spec: EmbedderSpec
    vector_table: str
    # Where a remote embedder is called; None for a local one, and on a read
    # that only shows the index.
    endpoint: RemoteEndpoint | None = None


def active_index(session: Session) -> ActiveIndex | None:
    """The index search reads and ingest writes. None before onboarding chooses."""
    row = session.scalars(
        select(EmbeddingIndex).where(EmbeddingIndex.state == IndexState.ACTIVE)
    ).one_or_none()
    if row is None:
        return None
    return ActiveIndex(row.id, EmbedderSpec.model_validate(row.spec), row.vector_table)


def require_active_index(session: Session) -> ActiveIndex:
    """The index, ready to embed with: a remote one's server is resolved here,
    so a host turned off in Settings stops ingest and search, and says why."""
    index = active_index(session)
    if index is None:
        raise EmbeddingNotChosenError
    if index.spec.source is Source.REMOTE:
        return replace(index, endpoint=endpoint_for(session, index.spec))
    return index
