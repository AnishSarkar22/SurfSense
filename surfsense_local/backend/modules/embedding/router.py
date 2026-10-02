from fastapi import APIRouter
from sqlalchemy.orm import Session

from api.dependencies import SessionDep, transact
from modules.embedding.active import active_index
from modules.embedding.schemas import EmbeddingIndexRead, IndexRead
from modules.embedding.spec import Source
from modules.llm.catalog.local.manifest import load_local_manifest
from modules.llm.models import ProviderConnection

router = APIRouter(prefix="/embedding", tags=["embedding"])


@router.get(
    "/index",
    response_model=EmbeddingIndexRead,
    summary="Read which embedding model the library is built with",
)
async def read_index(session: SessionDep) -> EmbeddingIndexRead:
    return await transact(session, _read)


def _read(session: Session) -> EmbeddingIndexRead:
    index = active_index(session)
    if index is None:
        return EmbeddingIndexRead(active=None)
    spec = index.spec
    if spec.source is Source.REMOTE:
        connection = session.get(ProviderConnection, spec.connection_id)
        return EmbeddingIndexRead(
            active=IndexRead(
                name=spec.model or spec.id,
                spec=spec,
                server=connection.label if connection is not None else None,
            )
        )
    names = {m.id: m.name for m in load_local_manifest().models}
    # A Hugging Face pick is named by its repo; its install name is ours.
    return EmbeddingIndexRead(
        active=IndexRead(name=names.get(spec.id, spec.repo or spec.id), spec=spec)
    )
