"""Ollama: `/api/show` lists `"embedding"` among a model's capabilities, which
it derives from the GGUF header's pooling type. `/api/tags` only says so
reliably since 0.34.1, so each listed model is asked."""

import asyncio

import httpx

from modules.embedding.remote.recognise.recognised import Recognised
from modules.embedding.spec import Identified


async def ollama_embedders(
    client: httpx.AsyncClient, root: str
) -> list[Recognised] | None:
    version = await client.get(f"{root}/api/version")
    if version.status_code != 200 or "version" not in _json(version):
        return None
    tags = await client.get(f"{root}/api/tags")
    names = [m.get("name") for m in _json(tags).get("models") or ()]
    names = [n for n in names if isinstance(n, str)]
    shown = await asyncio.gather(
        *(client.post(f"{root}/api/show", json={"model": n}) for n in names)
    )
    return [
        Recognised(name, Identified.DECLARED)
        for name, reply in zip(names, shown, strict=True)
        if "embedding" in (_json(reply).get("capabilities") or ())
    ]


def _json(reply: httpx.Response) -> dict:
    try:
        body = reply.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}
