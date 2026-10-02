"""Which models on a connection embed, and how SurfSense knows.

The first source that answers decides: the server's own word (`declared`), then
the catalog's `family` (`declared`), then the name (`inferred`). A model none
of them vouches for is left out of the list; typed by hand, it is `unverified`.
"""

import asyncio
from collections.abc import Awaitable

import httpx

from modules.embedding.remote.recognise.by_catalog import (
    catalog_entry,
    family_says_embedder,
)
from modules.embedding.remote.recognise.by_name import named_like_an_embedder
from modules.embedding.remote.recognise.recognised import Recognised
from modules.embedding.remote.recognise.server_root import server_root
from modules.embedding.remote.recognise.servers.lmstudio import lmstudio_embedders
from modules.embedding.remote.recognise.servers.ollama import ollama_embedders
from modules.embedding.remote.recognise.servers.openrouter import (
    openrouter_embedders,
)
from modules.embedding.remote.recognise.servers.tei import tei_embedders
from modules.embedding.spec import Identified
from modules.llm.catalog.remote.rows import CUSTOM
from modules.llm.connections.key_headers import key_headers
from modules.llm.connections.service import DISCOVERY_TIMEOUT, discover_models
from modules.llm.models import ProviderConnection


async def embedders_on(connection: ProviderConnection) -> list[Recognised]:
    """Raises `httpx.HTTPError` or `ValueError` when nothing can list the server."""
    declared = await _server_says(connection.base_url, connection.api_key)
    if declared is not None:
        return sorted(declared, key=lambda found: found.name.casefold())
    provider = _provider(connection)
    found = [
        recognised
        for model in await discover_models(connection)
        if (recognised := _judged(model.name, provider)) is not None
    ]
    return sorted(found, key=lambda each: each.name.casefold())


async def recognise(connection: ProviderConnection, model: str) -> Recognised:
    """One model, listed or typed by hand."""
    try:
        listed = {found.name: found for found in await embedders_on(connection)}
    except (httpx.HTTPError, ValueError):
        listed = {}
    return (
        listed.get(model)
        or _judged(model, _provider(connection))
        or Recognised(model, Identified.UNVERIFIED)
    )


def _judged(model: str, provider: str | None) -> Recognised | None:
    entry = catalog_entry(model, provider)
    context = entry.context if entry is not None else None
    if family_says_embedder(entry):
        return Recognised(model, Identified.DECLARED, context)
    if named_like_an_embedder(model):
        return Recognised(model, Identified.INFERRED, context)
    return None


async def serves_embedders(base_url: str, api_key: str | None) -> bool:
    """Whether a server with no `/models` still declares embedders, as TEI does."""
    return bool(await _server_says(base_url, api_key))


async def _server_says(base_url: str, api_key: str | None) -> list[Recognised] | None:
    """The first server kind that recognises itself; None for a server with no
    word of its own, such as llama-server, vLLM or a hosted API."""
    root = server_root(base_url)
    async with httpx.AsyncClient(
        timeout=DISCOVERY_TIMEOUT, headers=key_headers(base_url, api_key)
    ) as client:
        answers = await asyncio.gather(
            _quiet(tei_embedders(client, root)),
            _quiet(ollama_embedders(client, root)),
            _quiet(lmstudio_embedders(client, root)),
            _quiet(openrouter_embedders(client, base_url)),
        )
    return next((answer for answer in answers if answer is not None), None)


async def _quiet(asked: Awaitable[list[Recognised] | None]) -> list[Recognised] | None:
    """A server of another kind answers 404 or nothing; that is not an error."""
    try:
        return await asked
    except (httpx.HTTPError, ValueError):
        return None


def _provider(connection: ProviderConnection) -> str | None:
    return (
        None if connection.catalog_provider == CUSTOM else connection.catalog_provider
    )
