"""Embedders on a connected server: which models embed, and checking one.

Egress gated like every connection route; the model locks when onboarding
finishes with the choice the check returns.
"""

import httpx
from fastapi import APIRouter, HTTPException, status

from api.dependencies import SessionDep, transact
from modules.embedding.remote.call import RemoteEmbeddingError
from modules.embedding.remote.check import RefusedEmbedderError, check
from modules.embedding.remote.recognise.listing import embedders_on, recognise
from modules.embedding.remote.schemas import (
    RemoteCheckRead,
    RemoteCheckWrite,
    RemoteEmbedderRead,
)
from modules.llm.connections.discovery_failure import discovery_failure
from modules.llm.connections.router import allowed_connection

router = APIRouter(prefix="/embedding/remote", tags=["embedding"])


@router.get(
    "/connections/{connection_id}/models",
    response_model=list[RemoteEmbedderRead],
    summary="List the embedding models a connected server offers",
)
async def list_embedders(
    connection_id: int, session: SessionDep
) -> list[RemoteEmbedderRead]:
    connection = await transact(session, allowed_connection, connection_id)
    try:
        found = await embedders_on(connection)
    except httpx.HTTPError as error:
        raise discovery_failure(error) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return [
        RemoteEmbedderRead(name=f.name, identified=f.identified, context=f.context)
        for f in found
    ]


@router.post(
    "/check",
    response_model=RemoteCheckRead,
    summary="Check a server's model before onboarding locks it",
)
async def check_embedder(
    payload: RemoteCheckWrite, session: SessionDep
) -> RemoteCheckRead:
    connection = await transact(session, allowed_connection, payload.connection_id)
    found = await recognise(connection, payload.model.strip())
    try:
        spec = await check(connection, found)
    except RefusedEmbedderError as refused:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(refused)
        ) from refused
    except RemoteEmbeddingError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return RemoteCheckRead(
        choice=spec.id,
        name=found.name,
        identified=spec.identified,
        dimension=spec.dimension,
    )
